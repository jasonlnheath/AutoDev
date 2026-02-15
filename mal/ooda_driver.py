#!/usr/bin/env python
"""
OODA Driver - Autonomous Development Loop

Implements the OODA (Observe, Orient, Decide, Act) loop for iterative AI development.

OBSERVE: Read current code, run tests, capture errors
ORIENT:  Query byterover context tree for relevant patterns
DECIDE:  Generate patch based on context + errors (LLM)
ACT:     Apply patch, verify tests pass
"""

import subprocess
import sys
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional


class OODADriver:
    """Autonomous development loop driver"""

    def __init__(self, project_dir: str, step_file: str, test_file: str):
        self.project_dir = Path(project_dir)
        self.step_file = self.project_dir / step_file
        self.test_file = self.project_dir / test_file
        self.iteration = 0
        self.max_iterations = 10

        # Context for this session
        self.context = {
            "errors_seen": [],
            "patches_applied": [],
            "test_results": [],
        }

    def log(self, message: str, level: str = "INFO"):
        """Log a message with timestamp and iteration"""
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] [Iter {self.iteration}] [{level}] {message}")

    def observe(self) -> Dict[str, Any]:
        """
        OBSERVE phase:
        - Read current code
        - Run tests
        - Capture errors/failures
        """
        self.log("OBSERVE: Reading code and running tests...")

        # Read current code
        try:
            with open(self.step_file, 'r') as f:
                code = f.read()
        except Exception as e:
            self.log(f"Failed to read code: {e}", "ERROR")
            return {"error": str(e)}

        # Run tests
        test_result = self.run_tests()

        return {
            "code": code,
            "test_output": test_result["output"],
            "test_passed": test_result["passed"],
            "test_failed": test_result["failed"],
            "exit_code": test_result["exit_code"],
        }

    def orient(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        """
        ORIENT phase:
        - Analyze errors
        - Query context tree for relevant patterns
        - Build context for patch generation
        """
        self.log("ORIENT: Analyzing errors and building context...")

        # Check if tests pass
        if observation["test_failed"] == 0:
            self.log("All tests passed!", "SUCCESS")
            return {"status": "complete"}

        # Extract error patterns
        errors = self.extract_errors(observation["test_output"])

        # In a full implementation, this would query byterover
        # For now, we track what we've seen
        for error in errors:
            if error not in self.context["errors_seen"]:
                self.context["errors_seen"].append(error)
                self.log(f"New error pattern: {error}", "WARN")

        return {
            "errors": errors,
            "context": self.context,
            "similar_issues": self.find_similar_issues(errors),
        }

    def decide(self, observation: Dict[str, Any], orientation: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        DECIDE phase:
        - Generate patch based on code + errors + context
        - (In full version, this uses LLM to generate the patch)
        """
        self.log("DECIDE: Generating patch...")

        if orientation.get("status") == "complete":
            return None

        # For demonstration, return what needs to be fixed
        # In full implementation, LLM would generate actual code patch
        errors = orientation.get("errors", [])

        return {
            "description": f"Fix {len(errors)} error(s)",
            "errors_to_fix": errors,
            # In full version: "patch": "generated_code_diff"
        }

    def act(self, observation: Dict[str, Any], decision: Optional[Dict[str, Any]]) -> bool:
        """
        ACT phase:
        - Apply patch to code
        - Run tests to verify
        - Update context
        """
        self.log("ACT: Applying patch...")

        if decision is None:
            # Complete!
            return True

        # For demonstration, just report what would be patched
        # In full implementation, this would apply actual code changes
        self.log(f"Would patch: {decision['description']}")
        self.log(f"Errors to fix: {decision['errors_to_fix']}")

        # Simulate patch application
        self.context["patches_applied"].append({
            "iteration": self.iteration,
            "errors": decision["errors_to_fix"],
        })

        return False  # Not complete yet

    def run_tests(self) -> Dict[str, Any]:
        """Run tests and return results"""
        try:
            result = subprocess.run(
                [sys.executable, "test.py", str(self.test_file), sys.executable, str(self.step_file)],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=self.project_dir
            )

            # Parse output for pass/fail counts
            output = result.stdout
            lines = output.split('\n')
            passed = 0
            failed = 0

            for line in lines:
                if "passed" in line and "failed" in line:
                    # Parse "Results: 24 passed, 0 failed"
                    import re
                    match = re.search(r'(\d+) passed, (\d+) failed', line)
                    if match:
                        passed = int(match.group(1))
                        failed = int(match.group(2))

            return {
                "output": output,
                "passed": passed,
                "failed": failed,
                "exit_code": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"output": "TIMEOUT", "passed": 0, "failed": 1, "exit_code": -1}
        except Exception as e:
            return {"output": str(e), "passed": 0, "failed": 1, "exit_code": -1}

    def extract_errors(self, test_output: str) -> List[str]:
        """Extract error patterns from test output"""
        errors = []
        for line in test_output.split('\n'):
            if "[FAIL]" in line:
                # Extract the error description
                parts = line.split("Expected:", 1)
                if len(parts) > 1:
                    expected = parts[1].split("Got:")[0].strip()
                    errors.append(f"Expected: {expected}")
        return errors

    def find_similar_issues(self, errors: List[str]) -> List[str]:
        """Find similar issues from context (placeholder for byterover integration)"""
        # In full implementation, this would query the byterover context tree
        return []

    def run(self) -> Dict[str, Any]:
        """Run the OODA loop until tests pass or max iterations reached"""
        self.log("Starting OODA loop...")
        self.log(f"Step file: {self.step_file}")
        self.log(f"Test file: {self.test_file}")
        self.log(f"Max iterations: {self.max_iterations}")
        print()

        complete = False

        while self.iteration < self.max_iterations:
            self.iteration += 1

            # OBSERVE
            observation = self.observe()
            if "error" in observation:
                self.log(f"Observation failed: {observation['error']}", "ERROR")
                break

            # ORIENT
            orientation = self.orient(observation)
            if orientation.get("status") == "complete":
                complete = True
                break

            # DECIDE
            decision = self.decide(observation, orientation)
            if decision is None:
                complete = True
                break

            # ACT
            if self.act(observation, decision):
                complete = True
                break

            print()

        # Summary
        self.log("=" * 50)
        if complete:
            self.log("OODA loop complete - tests pass!", "SUCCESS")
        else:
            self.log(f"OODA loop stopped after {self.max_iterations} iterations", "WARN")

        return {
            "iterations": self.iteration,
            "complete": complete,
            "context": self.context,
        }


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="OODA Driver for autonomous development")
    parser.add_argument("step", help="Step file (e.g., step0.py)")
    parser.add_argument("test", help="Test file (e.g., tests/step0_repl.mal)")
    parser.add_argument("--max-iterations", type=int, default=10,
                       help="Maximum iterations (default: 10)")
    parser.add_argument("--project-dir", default=".",
                       help="Project directory (default: current)")

    args = parser.parse_args()

    driver = OODADriver(args.project_dir, args.step, args.test)
    driver.max_iterations = args.max_iterations

    result = driver.run()

    # Exit with appropriate code
    sys.exit(0 if result["complete"] else 1)


if __name__ == "__main__":
    main()
