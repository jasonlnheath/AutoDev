"""
Progress monitoring for AutoDev iterations.

Track loop progress and provide human-readable status.
"""
import json
from pathlib import Path
from typing import Dict, List
from datetime import datetime


class ProgressMonitor:
    """Monitor and report OODA loop progress."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.log_path = project_root / "logs" / "iterations.jsonl"

    def get_history(self) -> List[dict]:
        """Get iteration history from logs."""
        if not self.log_path.exists():
            return []

        history = []
        with open(self.log_path, 'r') as f:
            for line in f:
                history.append(json.loads(line))
        return history

    def get_summary(self) -> dict:
        """Get summary of all iterations."""
        history = self.get_history()

        if not history:
            return {
                "total_iterations": 0,
                "successful_patches": 0,
                "failed_patches": 0,
                "success_rate": 0.0
            }

        successful = sum(1 for h in history if h.get("success"))

        return {
            "total_iterations": len(history),
            "successful_patches": successful,
            "failed_patches": len(history) - successful,
            "success_rate": successful / len(history),
            "latest_iteration": history[-1]
        }

    def print_report(self):
        """Print human-readable progress report."""
        summary = self.get_summary()

        print("\n" + "=" * 50)
        print("AutoDev Progress Report")
        print("=" * 50)
        print(f"Total Iterations: {summary['total_iterations']}")
        print(f"Successful Patches: {summary['successful_patches']}")
        print(f"Failed Patches: {summary['failed_patches']}")
        print(f"Success Rate: {summary['success_rate']:.1%}")

        if summary.get('latest_iteration'):
            latest = summary['latest_iteration']
            print(f"\nLatest Iteration: #{latest['iteration']}")
            status = "✓ PASS" if latest['success'] else "✗ FAIL"
            print(f"Status: {status}")

        print("=" * 50 + "\n")

    def watch(self):
        """Watch mode - continuously report progress."""
        import time

        try:
            while True:
                self.print_report()
                time.sleep(5)
        except KeyboardInterrupt:
            print("\nStopped watching.")
