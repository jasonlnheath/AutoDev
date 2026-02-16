#!/usr/bin/env python3
"""
Claude-Native OODA Loop - Uses Claude Code directly instead of external LLM APIs.

Run: python local_loop.py -f step4.py
"""
import json
import sys
import time
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from ooda.observe import Observer
from ooda.orient import Orienter
from ooda.act import Actor


def print_header(title: str):
    print(f"\n{'=' * 50}")
    print(f"{title:^50}")
    print(f"{'=' * 50}")


def print_section(name: str):
    print(f"\n[{name}]")


def run_claude_native_loop(
    target_file: str = "step4.py",
    max_iterations: int = 20
):
    """
    Run OODA loop using Claude Code directly for patch generation.
    """
    project_root = Path(__file__).parent

    # Initialize phases
    observer = Observer(project_root)
    orienter = Orienter(project_root)
    actor = Actor(project_root, "mal")

    print_header("Claude-Native OODA Loop")
    print(f"Target: {target_file}")
    print(f"Max iterations: {max_iterations}")
    print(f"Mode: Local (Claude Code generates patches)")

    successful_patches = 0
    iteration = 0

    for iteration in range(1, max_iterations + 1):
        print_header(f"Iteration {iteration}/{max_iterations}")

        # === OBSERVE ===
        print_section("OBSERVE")
        success, output = observer.run_tests()

        if success:
            print(f"\n[SUCCESS] All tests passing!")
            break

        parsed = observer.parse_mal_test_output(output)
        current_code = observer.read_file(target_file)
        missing = parsed.get("missing_functions", [])

        print(f"  Tests: {parsed.get('passed', 0)} passed, {parsed.get('failed', 0)} failed")
        print(f"  Missing functions: {', '.join(missing[:10])}")
        if len(missing) > 10:
            print(f"  ... and {len(missing) - 10} more")

        # === ORIENT ===
        print_section("ORIENT")
        context = orienter.query_context(output, target_file, iteration)

        similar_count = len(context.get("similar_errors", []))
        lessons_count = len(context.get("lessons_learned", []))
        print(f"  Similar past errors: {similar_count}")
        print(f"  Lessons available: {lessons_count}")

        # === DECIDE (Claude generates patch) ===
        print_section("DECIDE")
        print("\n  >>> CLAUDE: Please generate a patch based on this context:\n")

        # Show context to Claude
        print("  " + "="*46)
        print("  CONTEXT FOR PATCH GENERATION")
        print("  " + "="*46)

        print(f"\n  File: {target_file}")
        print(f"  Missing functions: {missing[:15]}")
        print(f"  Current step: {observer.get_current_step()}")

        # Show relevant code section
        print("\n  Current code (EVAL section):")
        lines = current_code.split('\n')
        in_eval = False
        eval_lines = []
        for i, line in enumerate(lines):
            if 'def EVAL(' in line:
                in_eval = True
            if in_eval:
                eval_lines.append(f"  {i+1:4}: {line}")
                if line.strip() == 'return evaluated' or line.strip().startswith('return eval_ast'):
                    break
        for line in eval_lines[-50:]:  # Show last 50 lines of EVAL
            print(line)

        # Show similar errors if any
        if context.get("similar_errors"):
            print("\n  Similar past errors:")
            for err in context.get("similar_errors", [])[:3]:
                print(f"    - {err.get('error_type', 'unknown')}: {err.get('success', False)}")

        print("\n  " + "="*46)
        print("\n  >>> CLAUDE: Use the Edit tool to add the missing functions.")
        print("  >>> Target the appropriate location in EVAL (for special forms)")
        print("  >>> or add as built-in functions (for list, count, etc.)")
        print("  >>> Then type 'CONTINUE' to proceed to ACT phase\n")

        # Wait for Claude to make changes
        input("\n  [Press Enter after Claude has applied the patch, or type 'SKIP' to skip]")

        # === ACT ===
        print_section("ACT")

        # Re-read the file to get current state
        new_code = observer.read_file(target_file)

        if new_code == current_code:
            print("  [WARN] No changes detected - skipping verification")
            continue

        # Verify the changes
        print("  Verifying patch...")

        # Run tests again
        verify_success, verify_output = observer.run_tests()

        if verify_success:
            print("  [SUCCESS] Tests pass!")
            successful_patches += 1
            # Record success
            orienter.record_result(output, "patch applied", target_file, True, iteration)
        else:
            verify_parsed = observer.parse_mal_test_output(verify_output)
            still_missing = verify_parsed.get("missing_functions", [])
            print(f"  [FAIL] Tests still failing")
            print(f"  Still missing: {len(still_missing)} functions")

            # Record failure
            orienter.record_result(output, "patch failed", target_file, False, iteration)

        # Create iteration record
        orienter.create_iteration_record(
            iteration=iteration,
            observe={
                "tests_passing": verify_success,
                "missing_functions": still_missing,
                "passed": verify_parsed.get("passed", 0) if not verify_success else parsed.get("passed", 0),
                "failed": verify_parsed.get("failed", 0) if not verify_success else 0
            },
            orient=context,
            decide={"model": "claude-native", "attempts": 1},
            act={"success": verify_success, "verified": verify_success},
            outcome="success" if verify_success else "failed"
        )

    # Final report
    print_header("Final Report")
    print(f"\nTotal iterations: {iteration}")
    print(f"Successful patches: {successful_patches}")
    print(f"Tests passing: {'YES' if success else 'NO'}")

    if not success:
        print(f"\nRemaining missing functions: {missing}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Claude-Native OODA Loop")
    parser.add_argument("--file", "-f", default="step4.py", help="Target file")
    parser.add_argument("--max-iterations", "-n", type=int, default=20, help="Max iterations")
    args = parser.parse_args()

    try:
        run_claude_native_loop(args.file, args.max_iterations)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
