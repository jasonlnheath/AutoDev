#!/usr/bin/env python3
"""
AutoDev - Autonomous Development Loop using OODA Cycle.

Main entry point for the autonomous development system.
Integrates Observe, Orient, Decide, Act phases with progress monitoring.
"""
import json
import argparse
import time
import signal
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from ooda.observe import Observer
from ooda.orient import Orienter
from ooda.decide import Decider, PatchResult
from ooda.act import Actor, ActResult
from monitor.progress import ProgressMonitor


@dataclass
class LoopResult:
    """Result of the OODA loop execution."""
    success: bool
    total_iterations: int
    successful_patches: int
    failed_patches: int
    final_state: str  # "tests_passing", "max_iterations", "error", "timeout"
    error_message: Optional[str]
    duration_seconds: float
    statistics: Dict[str, Any]


class SafetyLimits:
    """Enforce safety limits on the OODA loop."""

    def __init__(self, config_path: Path):
        config = json.loads(config_path.read_text())
        self.max_iterations = config["iteration"]["max_iterations"]
        self.timeout_minutes = config["iteration"]["timeout_minutes"]
        self.require_human_approval = config["safety"]["require_human_approval"]
        self.auto_rollback = config["safety"]["auto_rollback"]

    def check_iteration_limit(self, current: int) -> bool:
        """Check if we've exceeded iteration limit."""
        return current >= self.max_iterations

    def check_timeout(self, start_time: float) -> bool:
        """Check if we've exceeded timeout."""
        elapsed = (time.time() - start_time) / 60
        return elapsed >= self.timeout_minutes


class OODALoop:
    """
    Main OODA Loop orchestrator.

    Coordinates Observe, Orient, Decide, Act phases with:
    - Progress monitoring
    - Safety limits
    - Detailed logging
    - Human-in-the-loop intervention points
    """

    def __init__(
        self,
        project_root: Optional[Path] = None,
        target_dir: str = "mal",
        verbose: bool = False
    ):
        self.project_root = project_root or Path(__file__).parent
        self.target_dir = target_dir
        self.verbose = verbose

        # Load configuration
        config_path = self.project_root / "config"
        self.limits = SafetyLimits(config_path / "limits.json")

        # Initialize OODA phases
        self.observer = Observer(self.project_root)
        self.orient = Orienter(self.project_root)
        self.decider = Decider(self.project_root)
        self.actor = Actor(self.project_root, target_dir)
        self.monitor = ProgressMonitor(self.project_root)

        # State tracking
        self.start_time = None
        self.current_iteration = 0
        self.should_stop = False

        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._handle_interrupt)

    def _handle_interrupt(self, signum, frame):
        """Handle Ctrl+C gracefully."""
        print("\n\nInterrupt received. Finishing current iteration...")
        self.should_stop = True

    def _log(self, message: str, level: str = "INFO"):
        """Log message with timestamp if verbose."""
        if self.verbose or level in ("WARN", "ERROR"):
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] {level}: {message}")

    def _print_header(self, title: str):
        """Print a section header."""
        width = 50
        print(f"\n{'=' * width}")
        print(f"{title:^{width}}")
        print(f"{'=' * width}")

    def run(
        self,
        target_file: Optional[str] = None,
        max_iterations: Optional[int] = None
    ) -> LoopResult:
        """
        Run the OODA loop until tests pass or limits reached.

        Args:
            target_file: Specific file to fix (if None, auto-detect)
            max_iterations: Override default max iterations

        Returns:
            LoopResult with complete execution details
        """
        self.start_time = time.time()
        max_iter = max_iterations or self.limits.max_iterations

        self._print_header("AutoDev - OODA Loop Starting")
        print(f"Project: {self.project_root}")
        print(f"Target directory: {self.target_dir}")
        print(f"Max iterations: {max_iter}")
        print(f"Timeout: {self.limits.timeout_minutes} minutes")

        successful_patches = 0
        failed_patches = 0

        for iteration in range(1, max_iter + 1):
            if self.should_stop:
                break

            if self.limits.check_iteration_limit(iteration - 1):
                self._log("Maximum iterations reached", "WARN")
                break

            if self.limits.check_timeout(self.start_time):
                self._log("Timeout reached", "WARN")
                break

            self.current_iteration = iteration
            self._print_header(f"Iteration {iteration}/{max_iter}")

            # === OBSERVE ===
            print("\n[OBSERVE] Checking current state...")
            observe_data = self._observe_phase(target_file)

            if observe_data["tests_passing"]:
                return self._create_result(
                    success=True,
                    total_iterations=iteration,
                    successful_patches=successful_patches,
                    failed_patches=failed_patches,
                    final_state="tests_passing"
                )

            # === ORIENT ===
            print("\n[ORIENT] Querying context memory...")
            orient_data = self._orient_phase(observe_data, target_file)

            # Display context info
            similar_count = len(orient_data.get("similar_errors", []))
            if similar_count > 0:
                print(f"  Found {similar_count} similar past errors")

            lessons_count = len(orient_data.get("lessons_learned", []))
            if lessons_count > 0:
                print(f"  {lessons_count} lessons learned available")

            # === DECIDE ===
            print("\n[DECIDE] Generating patch...")
            decide_data = self._decide_phase(observe_data, orient_data)

            if not decide_data["patch_result"]:
                return self._create_result(
                    success=False,
                    total_iterations=iteration,
                    successful_patches=successful_patches,
                    failed_patches=failed_patches,
                    final_state="error",
                    error_message="Failed to generate patch"
                )

            patch_result = decide_data["patch_result"]
            print(f"  Model: {patch_result.model_used}")
            print(f"  Attempts: {patch_result.attempts}")
            print(f"  Patch size: {len(patch_result.patch)} bytes")

            # Human approval check
            if self.limits.require_human_approval:
                if not self._request_approval(patch_result.patch):
                    print("  Patch rejected by user")
                    failed_patches += 1
                    continue

            # === ACT ===
            print("\n[ACT] Applying patch and verifying...")
            act_result = self._act_phase(
                observe_data, orient_data, decide_data, iteration
            )

            if act_result.success:
                successful_patches += 1
                print(f"  [OK] Patch applied and verified!")
            else:
                failed_patches += 1
                print(f"  [FAIL] Patch failed: {act_result.errors[0] if act_result.errors else 'Unknown'}")

            # Record result for learning
            self.orient.record_result(
                error=observe_data.get("error_output", ""),
                fix=patch_result.patch,
                file_path=observe_data.get("target_file", ""),
                success=act_result.success,
                iteration=iteration
            )

            # Create iteration record
            self.orient.create_iteration_record(
                iteration=iteration,
                observe=observe_data,
                orient=orient_data,
                decide=decide_data,
                act=asdict(act_result),
                outcome="success" if act_result.success else "failed"
            )

        # Loop ended without success
        return self._create_result(
            success=False,
            total_iterations=max_iter,
            successful_patches=successful_patches,
            failed_patches=failed_patches,
            final_state="max_iterations"
        )

    def _observe_phase(self, target_file: Optional[str]) -> Dict[str, Any]:
        """Execute OBSERVE phase with Docker-based Mal testing."""
        # Run actual Mal tests via Docker
        success, output = self.observer.run_tests()

        # Parse the test output
        parsed = self.observer.parse_mal_test_output(output)

        # Determine target file
        if target_file:
            detected_file = target_file
        else:
            # Auto-detect from current step
            current_step = self.observer.get_current_step()
            detected_file = f"step{current_step}.py" if current_step else "step3.py"

        # Get current code
        current_code = ""
        try:
            if detected_file:
                current_code = self.observer.read_file(detected_file)
        except Exception as e:
            self._log(f"Could not read file {detected_file}: {e}", "WARN")

        return {
            "tests_passing": success,
            "error_output": output,
            "target_file": detected_file,
            "current_code": current_code,
            "missing_functions": parsed.get("missing_functions", []),
            "passed": parsed.get("passed", 0),
            "failed": parsed.get("failed", 0),
            "timestamp": datetime.now().isoformat()
        }

    def _orient_phase(
        self,
        observe_data: Dict[str, Any],
        target_file: Optional[str]
    ) -> Dict[str, Any]:
        """Execute ORIENT phase."""
        file_path = target_file or observe_data.get("target_file", "")
        error = observe_data.get("error_output", "")

        context = self.orient.query_context(
            error_message=error,
            file_path=file_path,
            iteration=self.current_iteration
        )

        return context

    def _decide_phase(
        self,
        observe_data: Dict[str, Any],
        orient_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute DECIDE phase."""
        file_path = observe_data.get("target_file", "")
        current_code = observe_data.get("current_code", "")
        error = observe_data.get("error_output", "")
        missing = observe_data.get("missing_functions", [])
        current_step = self.observer.get_current_step()

        if not file_path:
            return {"patch_result": None, "error": "No target file"}

        patch_result = self.decider.generate_patch(
            file_path=file_path,
            current_code=current_code,
            error_message=error,
            context=orient_data,
            test_name="",
            missing_functions=missing,
            current_step=current_step
        )

        return {
            "patch_result": patch_result,
            "error": None if patch_result else "Generation failed"
        }

    def _act_phase(
        self,
        observe_data: Dict[str, Any],
        orient_data: Dict[str, Any],
        decide_data: Dict[str, Any],
        iteration: int
    ) -> ActResult:
        """Execute ACT phase."""
        file_path = observe_data.get("target_file", "")
        patch_result = decide_data.get("patch_result")

        if not patch_result:
            return ActResult(
                success=False,
                patch_applied=False,
                verification_passed=False,
                rollback_performed=False,
                output="",
                errors=["No patch to apply"],
                file_modified=file_path,
                iteration=iteration
            )

        return self.actor.act(
            file_path=file_path,
            diff=patch_result.patch,
            iteration=iteration,
            observe_data=observe_data,
            orient_data=orient_data,
            decide_data={"model": patch_result.model_used, "attempts": patch_result.attempts}
        )

    def _detect_file(self, error_output: str) -> Optional[str]:
        """Detect target file from error output."""
        for line in error_output.split('\n'):
            if '.py' in line:
                # Extract file path
                parts = line.split()
                for part in parts:
                    if part.endswith('.py'):
                        # Clean up the path
                        path = part.strip(':').strip('"').strip("'")
                        return path
        return None

    def _request_approval(self, patch: str) -> bool:
        """Request human approval for patch."""
        print("\n  --- Patch Preview ---")
        lines = patch.split('\n')
        for line in lines[:20]:  # Show first 20 lines
            print(f"  {line}")
        if len(lines) > 20:
            print(f"  ... ({len(lines) - 20} more lines)")
        print("  --- End Preview ---\n")

        while True:
            response = input("  Apply this patch? [y/n] ").lower().strip()
            if response in ('y', 'yes'):
                return True
            elif response in ('n', 'no'):
                return False
            print("  Please enter 'y' or 'n'")

    def _create_result(
        self,
        success: bool,
        total_iterations: int,
        successful_patches: int,
        failed_patches: int,
        final_state: str,
        error_message: Optional[str] = None
    ) -> LoopResult:
        """Create LoopResult with statistics."""
        duration = time.time() - self.start_time

        # Gather statistics from all phases
        decide_stats = self.decider.get_statistics()
        act_stats = self.actor.get_statistics()
        orient_stats = self.orient.get_statistics()

        statistics = {
            "decide": decide_stats,
            "act": act_stats,
            "orient": orient_stats,
            "duration_seconds": duration,
            "success_rate": successful_patches / max(1, (successful_patches + failed_patches))
        }

        return LoopResult(
            success=success,
            total_iterations=total_iterations,
            successful_patches=successful_patches,
            failed_patches=failed_patches,
            final_state=final_state,
            error_message=error_message,
            duration_seconds=duration,
            statistics=statistics
        )


def main():
    """CLI entry point for AutoDev."""
    parser = argparse.ArgumentParser(
        description="AutoDev - Autonomous Development Loop",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Run with defaults
  %(prog)s -f test.py              # Fix specific file
  %(prog)s --max-iterations 5      # Limit iterations
  %(prog)s --verbose               # Verbose output
  %(prog)s --watch                 # Watch progress
        """
    )

    parser.add_argument(
        "--file", "-f",
        help="Specific file to fix"
    )
    parser.add_argument(
        "--max-iterations", "-n",
        type=int,
        help="Maximum iterations (overrides config)"
    )
    parser.add_argument(
        "--target-dir", "-d",
        default="mal",
        help="Target directory containing code (default: mal)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--watch", "-w",
        action="store_true",
        help="Watch mode - show progress dashboard"
    )
    parser.add_argument(
        "--approve", "-a",
        action="store_true",
        help="Require human approval for each patch"
    )

    args = parser.parse_args()

    # Watch mode
    if args.watch:
        monitor = ProgressMonitor(Path(__file__).parent)
        try:
            monitor.watch()
        except KeyboardInterrupt:
            print("\nStopped watching.")
        return

    # Run OODA loop
    loop = OODALoop(verbose=args.verbose, target_dir=args.target_dir)

    # Override config if requested
    if args.approve:
        loop.limits.require_human_approval = True

    result = loop.run(target_file=args.file, max_iterations=args.max_iterations)

    # Print final report
    print("\n" + "=" * 50)
    print("AutoDev Execution Complete".center(50))
    print("=" * 50)
    print(f"\nFinal State: {result.final_state}")
    print(f"Iterations: {result.total_iterations}")
    print(f"Successful Patches: {result.successful_patches}")
    print(f"Failed Patches: {result.failed_patches}")
    print(f"Duration: {result.duration_seconds:.1f} seconds")

    if result.statistics.get("success_rate"):
        print(f"Success Rate: {result.statistics['success_rate']:.1%}")

    print()

    # Show progress report
    loop.monitor.print_report()

    if result.success:
        print("[SUCCESS] All tests passing!")
        exit(0)
    else:
        print(f"[FAILED] {result.error_message or 'Loop did not complete successfully'}")
        exit(1)


if __name__ == "__main__":
    main()
