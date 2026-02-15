"""
OBSERVE Phase: Read code, run tests, capture errors.

Gather information about the current state of the codebase.
"""
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple, List
import json


class Observer:
    """Observe codebase state: run tests, capture errors, read code."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.mal_dir = project_root / "mal"

    def run_tests(self) -> Tuple[bool, str]:
        """Run Mal tests and return (success, output)."""
        test_file = self.mal_dir / "runtest.py"
        result = subprocess.run(
            [sys.executable, str(test_file)],
            cwd=str(self.mal_dir),
            capture_output=True,
            text=True
        )
        return result.returncode == 0, result.stdout + result.stderr

    def get_failed_tests(self, test_output: str) -> List[str]:
        """Parse test output to extract failed test names."""
        failed = []
        for line in test_output.split('\n'):
            if 'FAIL' in line or 'ERROR' in line:
                # Extract test name from output
                parts = line.split()
                if parts:
                    failed.append(parts[-1])
        return failed

    def read_file(self, file_path: str) -> str:
        """Read source file content."""
        full_path = self.mal_dir / file_path
        return full_path.read_text()

    def capture_error_context(self, test_output: str) -> dict:
        """Capture structured error context for the decide phase."""
        return {
            "test_output": test_output,
            "failed_tests": self.get_failed_tests(test_output),
            "timestamp": str(Path.ctime(Path.cwd()))
        }

    def get_code_snapshot(self) -> dict:
        """Get snapshot of current code state."""
        src_dir = self.mal_dir / "src"
        snapshot = {}
        if src_dir.exists():
            for py_file in src_dir.glob("*.py"):
                snapshot[str(py_file.relative_to(self.mal_dir))] = py_file.read_text()
        return snapshot
