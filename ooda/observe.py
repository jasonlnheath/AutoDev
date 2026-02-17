"""
OBSERVE Phase: Read code, run tests, capture errors.

Gather information about the current state of the codebase.
Enhanced with Docker-based Mal test execution and output parsing.
"""
import subprocess
import sys
import re
import os
from pathlib import Path
from typing import Optional, Tuple, List
import json


class Observer:
    """Observe codebase state: run tests, capture errors, read code."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.mal_dir = project_root / "mal"

    def run_mal_test(self, step_file: str, test_file: str) -> Tuple[bool, str]:
        """
        Run a specific Mal test against a step file using Docker.

        Args:
            step_file: Step file (e.g., "step4.py")
            test_file: Test file (e.g., "tests/step4_if_fn_do.mal")

        Returns:
            (success, output) tuple
        """
        # Windows-compatible Docker command
        if os.name == 'nt':  # Windows
            mal_path = self.mal_dir.resolve()
            # Use Windows path format (C:/...) for Docker volume mount
            docker_path = str(mal_path).replace('\\', '/')

            docker_cmd = [
                "docker", "run", "--rm", "-i",
                "-v", f"{docker_path}:/workspace",
                "python:3.14-slim",
                "bash", "-c",
                f"cd /workspace && python test.py {test_file} python {step_file}"
            ]
        else:  # Unix-like
            docker_cmd = [
                "docker", "run", "--rm", "-i",
                "-v", f"{self.mal_dir}:/workspace",
                "python:3.14-slim",
                "bash", "-c",
                f"cd /workspace && python test.py {test_file} python {step_file}"
            ]

        result = subprocess.run(
            docker_cmd,
            capture_output=True,
            text=True,
            timeout=120,
            shell=False
        )
        return result.returncode == 0, result.stdout + result.stderr

    def parse_mal_test_output(self, output: str) -> dict:
        """
        Parse Mal test output to extract structured information.

        Args:
            output: Raw test output

        Returns:
            Dict with passed, failed, missing_functions, etc.
        """
        result = {
            "passed": 0,
            "failed": 0,
            "missing_functions": [],
            "failed_tests": [],
            "errors": []
        }

        # Find summary line: "Results: X passed, Y failed"
        summary_match = re.search(r'Results:\s+(\d+)\s+passed,\s+(\d+)\s+failed', output)
        if summary_match:
            result["passed"] = int(summary_match.group(1))
            result["failed"] = int(summary_match.group(2))

        # Extract missing function names from failures
        # Pattern: [FAIL] Line N: (test)\n  Expected: ...\n  Got:      'function_name' not found
        # Note: There can be multiple spaces before the quote
        missing_pattern = r"Got:\s+['\"]([^'\"]+)['\"]\s+not found"
        for match in re.finditer(missing_pattern, output):
            func_name = match.group(1)
            if func_name not in result["missing_functions"]:
                result["missing_functions"].append(func_name)

        # Extract failed test lines
        fail_pattern = r'\[FAIL\] Line (\d+): (.+)'
        for match in re.finditer(fail_pattern, output):
            line_num = match.group(1)
            test_expr = match.group(2)
            result["failed_tests"].append({
                "line": line_num,
                "test": test_expr
            })

        return result

    def get_current_step(self) -> Optional[int]:
        """Find the highest numbered step file."""
        step_files = list(self.mal_dir.glob("step*.py"))
        if not step_files:
            return None

        step_nums = []
        for f in step_files:
            match = re.match(r'step(\d+)', f.stem)
            if match:
                step_nums.append(int(match.group(1)))

        return max(step_nums) if step_nums else None

    def get_next_test_file(self, current_step: int) -> str:
        """Get the test file for the next step."""
        test_map = {
            0: "tests/step0_repl.mal",
            1: "tests/step1_read_print.mal",
            2: "tests/step2_eval.mal",
            3: "tests/step3_env.mal",
            4: "tests/step4_if_fn_do.mal",
            5: "tests/step5_tco.mal",
            6: "tests/step6_file.mal",
            7: "tests/step7_quote.mal",
            8: "tests/step8_macros.mal",
            9: "tests/step9_try.mal",
            10: "tests/stepA_mal.mal",
        }
        return test_map.get(current_step, "")

    def run_tests(self, test_file: Optional[str] = None) -> Tuple[bool, str]:
        """
        Run Mal tests using Docker.

        Auto-detects the current step and runs appropriate tests.
        """
        current_step = self.get_current_step()
        if current_step is None:
            return False, "No step file found"

        step_file = f"step{current_step}.py"
        test_to_run = test_file or self.get_next_test_file(current_step)

        if not test_to_run:
            # For unknown steps, try step4
            test_to_run = "tests/step4_if_fn_do.mal"

        return self.run_mal_test(step_file, test_to_run)

    def get_failed_tests(self, test_output: str) -> List[str]:
        """Parse test output to extract failed test names."""
        failed = []
        for line in test_output.split('\n'):
            if '[FAIL]' in line or '[ERROR]' in line:
                # Extract test expression
                match = re.search(r'\[FAIL\] Line \d+: (.+)', line)
                if match:
                    failed.append(match.group(1))
        return failed

    def read_file(self, file_path: str) -> str:
        """Read source file content."""
        full_path = self.mal_dir / file_path
        return full_path.read_text()

    def capture_error_context(self, test_output: str) -> dict:
        """Capture structured error context for the decide phase."""
        parsed = self.parse_mal_test_output(test_output)

        return {
            "test_output": test_output,
            "failed_tests": self.get_failed_tests(test_output),
            "missing_functions": parsed.get("missing_functions", []),
            "passed": parsed.get("passed", 0),
            "failed": parsed.get("failed", 0),
            "timestamp": str(Path.ctime(Path.cwd()))
        }

    def get_code_snapshot(self) -> dict:
        """Get snapshot of current code state."""
        snapshot = {}
        for py_file in self.mal_dir.glob("step*.py"):
            snapshot[str(py_file.name)] = py_file.read_text()
        return snapshot
