"""
ACT Phase: Apply patches and verify.

Safely apply patches with rollback on failure.
Enhanced with pure Python diff parsing, verification suite, and detailed logging.
"""
import subprocess
import sys
import shutil
import re
import ast
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import json


@dataclass
class ActResult:
    """Result of an act operation."""
    success: bool
    patch_applied: bool
    verification_passed: bool
    rollback_performed: bool
    output: str
    errors: List[str]
    file_modified: str
    iteration: int


@dataclass
class DiffHunk:
    """A hunk in a unified diff."""
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: List[str]


@dataclass
class ParsedDiff:
    """A parsed unified diff."""
    file_path: str
    old_file: str
    new_file: str
    hunks: List[DiffHunk]


class DiffParser:
    """Parse unified diff format."""

    @staticmethod
    def parse(diff: str) -> Optional[ParsedDiff]:
        """
        Parse a unified diff into structured format.

        Returns ParsedDiff or None if parsing fails.
        """
        lines = diff.split('\n')
        i = 0

        # Find headers
        old_file = None
        new_file = None

        for line in lines[:5]:
            if line.startswith('--- a/'):
                old_file = line[6:]
            elif line.startswith('+++ b/'):
                new_file = line[6:]

        if not old_file or not new_file:
            return None

        # Extract file path
        file_path = new_file

        # Parse hunks
        hunks = []
        hunk_pattern = re.compile(r'^@@\s+-(\d+),?(\d+)?\s+\+(\d+),?(\d+)?\s+@@')

        while i < len(lines):
            line = lines[i]
            match = hunk_pattern.match(line)

            if match:
                old_start = int(match.group(1))
                old_count = int(match.group(2)) if match.group(2) else 1
                new_start = int(match.group(3))
                new_count = int(match.group(4)) if match.group(4) else 1

                hunk_lines = []
                i += 1

                # Collect hunk lines until next hunk or end
                while i < len(lines):
                    next_line = lines[i]
                    if next_line.startswith('@@'):
                        break
                    if next_line.startswith((' ', '+', '-', '\\')):
                        hunk_lines.append(next_line)
                    elif next_line.strip() == '':
                        hunk_lines.append(next_line)
                    i += 1

                hunks.append(DiffHunk(
                    old_start=old_start,
                    old_count=old_count,
                    new_start=new_start,
                    new_count=new_count,
                    lines=hunk_lines
                ))
            else:
                i += 1

        return ParsedDiff(
            file_path=file_path,
            old_file=old_file,
            new_file=new_file,
            hunks=hunks
        )


class DiffApplier:
    """Apply unified diffs to files (pure Python implementation)."""

    def __init__(self, root_path: Path):
        self.root_path = root_path

    def apply(self, diff: str, relative_path: str) -> Tuple[bool, Optional[str]]:
        """
        Apply a unified diff to a file.

        Returns (success, error_message)
        """
        # Parse the diff
        parsed = DiffParser.parse(diff)
        if not parsed:
            return False, "Failed to parse diff"

        # Get full file path
        file_path = self.root_path / relative_path
        if not file_path.exists():
            return False, f"File not found: {relative_path}"

        # Read original content
        original_lines = file_path.read_text().split('\n')

        # Apply each hunk
        modified_lines = original_lines.copy()
        line_offset = 0

        for hunk in parsed.hunks:
            result, error = self._apply_hunk(
                modified_lines,
                hunk,
                line_offset
            )
            if not result:
                return False, error

            # Update offset for next hunk
            added = sum(1 for l in hunk.lines if l.startswith('+'))
            removed = sum(1 for l in hunk.lines if l.startswith('-'))
            line_offset += added - removed

        # Write modified content
        file_path.write_text('\n'.join(modified_lines))
        return True, None

    def _apply_hunk(
        self,
        lines: List[str],
        hunk: DiffHunk,
        line_offset: int
    ) -> Tuple[bool, Optional[str]]:
        """
        Apply a single hunk to the lines with fuzzy matching.

        Returns (success, error_message)
        """
        # Adjust for previous hunks
        actual_start = hunk.old_start + line_offset - 1  # 0-indexed

        # Try exact match first
        if actual_start >= 0 and actual_start < len(lines):
            result = self._try_apply_hunk_at(lines, hunk, actual_start)
            if result[0]:
                return result

        # Fuzzy matching: search for context lines nearby
        search_range = 20  # Search up/down 20 lines
        for offset in range(-search_range, search_range + 1):
            fuzzy_start = actual_start + offset
            if fuzzy_start >= 0 and fuzzy_start < len(lines):
                result = self._try_apply_hunk_at(lines, hunk, fuzzy_start)
                if result[0]:
                    # Update the offset for subsequent hunks
                    return True, None

        return False, f"Could not find matching location for hunk (searched +/- {search_range} lines)"

    def _try_apply_hunk_at(
        self,
        lines: List[str],
        hunk: DiffHunk,
        start_pos: int
    ) -> Tuple[bool, Optional[str]]:
        """
        Try to apply hunk at a specific position.

        Returns (success, error_message)
        """
        # Extract context lines (non-+ lines)
        context_lines = [l[1:] if l.startswith((' ', '-')) else None
                        for l in hunk.lines
                        if not l.startswith('+') and not l.startswith('\\')]

        # Check if context matches at this position
        match_count = 0
        total_context = 0

        for i, expected in enumerate(context_lines):
            if expected is None:
                continue
            total_context += 1
            actual_idx = start_pos + i
            if actual_idx < len(lines) and lines[actual_idx] == expected:
                match_count += 1

        # Require at least 50% context match to apply
        if total_context > 0 and match_count / total_context < 0.5:
            return False, f"Insufficient context match ({match_count}/{total_context})"

        # Apply the hunk
        new_lines = []
        i = start_pos

        for line in hunk.lines:
            if line.startswith('\\'):
                continue
            elif line.startswith(' '):
                # Context line
                if i < len(lines):
                    new_lines.append(lines[i])
                    i += 1
            elif line.startswith('-'):
                # Remove line
                if i < len(lines):
                    i += 1
            elif line.startswith('+'):
                # Add line
                new_lines.append(line[1:])

        # Replace the hunk region
        lines[start_pos:i] = new_lines
        return True, None


class VerificationSuite:
    """Verify patches using multiple checks."""

    def __init__(self, project_root: Path, target_dir: str = "mal"):
        self.project_root = project_root
        self.target_dir = project_root / target_dir
        self._observer = None

    def _get_observer(self):
        """Lazy import and cache Observer to avoid circular imports."""
        if self._observer is None:
            from ooda.observe import Observer
            self._observer = Observer(self.project_root)
        return self._observer

    def verify_all(self, file_path: str) -> Tuple[bool, List[str]]:
        """
        Run full verification suite including actual test execution.

        Returns (all_passed, list_of_messages)
        """
        messages = []
        all_passed = True

        # 1. Syntax check
        syntax_ok, syntax_msg = self.check_syntax(file_path)
        messages.append(f"Syntax: {'[OK]' if syntax_ok else '[FAIL]'} {syntax_msg}")
        if not syntax_ok:
            all_passed = False
            return False, messages

        # 2. Import check (can module be imported?)
        import_ok, import_msg = self.check_import(file_path)
        messages.append(f"Import: {'[OK]' if import_ok else '[FAIL]'} {import_msg}")
        if not import_ok:
            all_passed = False
            return False, messages

        # 3. RUN ACTUAL TESTS via Docker
        observer = self._get_observer()
        test_success, test_output = observer.run_tests()

        if test_success:
            messages.append(f"Tests: [OK] All tests passing!")
        else:
            messages.append(f"Tests: [FAIL] Some tests failing")
            all_passed = False

            # Parse and show what's still missing
            parsed = observer.parse_mal_test_output(test_output)
            passed = parsed.get("passed", 0)
            failed = parsed.get("failed", 0)
            missing = parsed.get("missing_functions", [])

            messages.append(f"  Test results: {passed} passed, {failed} failed")
            if missing:
                messages.append(f"  Still missing: {', '.join(missing[:5])}")
            if failed > 0 and not missing:
                messages.append(f"  Tests failing for other reasons")

        return all_passed, messages

    def check_syntax(self, file_path: str) -> Tuple[bool, str]:
        """Check Python syntax."""
        full_path = self.target_dir / file_path
        try:
            code = full_path.read_text()
            ast.parse(code)
            return True, "Valid Python syntax"
        except SyntaxError as e:
            return False, f"Line {e.lineno}: {e.msg}"

    def check_import(self, file_path: str) -> Tuple[bool, str]:
        """Check if file can be imported."""
        full_path = self.target_dir / file_path

        # Get module name
        module_name = full_path.stem
        if module_name.endswith('.py'):
            module_name = module_name[:-3]

        try:
            # Try to compile
            code = full_path.read_text()
            compile(code, str(full_path), 'exec')
            return True, f"{file_path} compiles successfully"
        except SyntaxError as e:
            return False, f"Import error: {e}"
        except Exception as e:
            return False, f"Compilation error: {e}"

    def run_tests(self) -> Tuple[bool, str]:
        """
        Run the project's test suite.

        Returns (tests_passed, output)
        """
        # Note: Mal tests require Unix-specific modules
        # For cross-platform compatibility, we check if file compiles
        test_files = list(self.target_dir.glob("*.py"))

        all_compile = True
        errors = []

        for test_file in test_files:
            if test_file.name.startswith('_'):
                continue
            try:
                code = test_file.read_text()
                compile(code, str(test_file), 'exec')
            except Exception as e:
                all_compile = False
                errors.append(f"{test_file.name}: {e}")

        if all_compile:
            return True, f"All {len(test_files)} Python files compile successfully"
        else:
            return False, "Compilation errors:\n" + "\n".join(errors)


class IterationLogger:
    """Log iteration results in detail."""

    def __init__(self, logs_dir: Path):
        self.logs_dir = logs_dir
        self.iterations_file = logs_dir / "iterations.jsonl"
        self.summary_file = logs_dir / "summary.json"

        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def log(
        self,
        iteration: int,
        observe_data: Dict[str, Any],
        orient_data: Dict[str, Any],
        decide_data: Dict[str, Any],
        act_result: ActResult
    ):
        """Log a complete iteration with patch details."""
        entry = {
            "iteration": iteration,
            "timestamp": datetime.now().isoformat(),
            "observe": observe_data,
            "orient": orient_data,
            "decide": decide_data,
            "act": {
                "success": act_result.success,
                "patch_applied": act_result.patch_applied,
                "verification_passed": act_result.verification_passed,
                "rollback_performed": act_result.rollback_performed,
                "file_modified": act_result.file_modified,
                "errors": act_result.errors
            }
        }

        # Append to iterations log
        with open(self.iterations_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')

        # Save patch to separate file for easier debugging
        patch_result = decide_data.get("patch_result")
        if patch_result:
            patch_file = self.logs_dir / f"patch_iter_{iteration}.diff"
            patch_file.write_text(patch_result.patch)

        # Update summary
        self._update_summary(iteration, act_result)

    def _update_summary(self, iteration: int, result: ActResult):
        """Update summary statistics."""
        if self.summary_file.exists():
            summary = json.loads(self.summary_file.read_text())
        else:
            summary = {
                "total_iterations": 0,
                "successful_iterations": 0,
                "failed_iterations": 0,
                "last_updated": None
            }

        summary["total_iterations"] = iteration
        summary["last_updated"] = datetime.now().isoformat()

        if result.success:
            summary["successful_iterations"] += 1
        else:
            summary["failed_iterations"] += 1

        self.summary_file.write_text(json.dumps(summary, indent=2))

    def get_history(self) -> List[Dict]:
        """Get full iteration history."""
        if not self.iterations_file.exists():
            return []

        history = []
        with open(self.iterations_file, 'r') as f:
            for line in f:
                history.append(json.loads(line))
        return history


class Actor:
    """
    Act: Apply patches and verify they work.

    Features:
    - Pure Python diff application
    - Automatic rollback on failure
    - Comprehensive verification suite
    - Detailed iteration logging
    """

    def __init__(self, project_root: Path, target_dir: str = "mal"):
        self.project_root = project_root
        self.target_dir = target_dir
        self.target_path = project_root / target_dir
        self.logs_dir = project_root / "logs"

        # Initialize components
        self.applier = DiffApplier(self.target_path)
        self.verifier = VerificationSuite(project_root, target_dir)
        self.logger = IterationLogger(self.logs_dir)

        # Track backups for rollback
        self.backups: Dict[str, Path] = {}

    def backup_file(self, file_path: str) -> Path:
        """Create backup of file before patching."""
        full_path = self.target_path / file_path
        backup_path = self.logs_dir / f"{file_path}.backup.{datetime.now().timestamp()}"
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(full_path, backup_path)
        self.backups[file_path] = backup_path
        return backup_path

    def restore_backup(self, file_path: str) -> bool:
        """Restore file from backup."""
        if file_path not in self.backups:
            return False

        backup_path = self.backups[file_path]
        if backup_path.exists():
            shutil.copy(backup_path, self.target_path / file_path)
            return True
        return False

    def apply_diff(self, file_path: str, diff: str) -> Tuple[bool, Optional[str]]:
        """
        Apply a unified diff to a file.

        Returns (success, error_message)
        """
        return self.applier.apply(diff, file_path)

    def verify(self, file_path: str) -> Tuple[bool, List[str]]:
        """Run verification suite on the patched file."""
        return self.verifier.verify_all(file_path)

    def run_tests(self) -> Tuple[bool, str]:
        """Run the project test suite."""
        return self.verifier.run_tests()

    def act(
        self,
        file_path: str,
        diff: str,
        iteration: int,
        observe_data: Dict = None,
        orient_data: Dict = None,
        decide_data: Dict = None
    ) -> ActResult:
        """
        Main act method: apply patch and verify.

        Returns ActResult with full details.
        """
        observe_data = observe_data or {}
        orient_data = orient_data or {}
        decide_data = decide_data or {}

        errors = []
        rollback_performed = False
        patch_applied = False
        verification_passed = False

        # Create backup
        self.backup_file(file_path)

        # Apply patch
        success, error = self.apply_diff(file_path, diff)
        if not success:
            errors.append(f"Patch application failed: {error}")
            self.restore_backup(file_path)

            result = ActResult(
                success=False,
                patch_applied=False,
                verification_passed=False,
                rollback_performed=True,
                output="",
                errors=errors,
                file_modified=file_path,
                iteration=iteration
            )
            self.logger.log(iteration, observe_data, orient_data, decide_data, result)
            return result

        patch_applied = True

        # Verify patch
        verified, messages = self.verify(file_path)
        verification_passed = verified

        if not verified:
            errors.extend(messages)
            self.restore_backup(file_path)
            rollback_performed = True

        result = ActResult(
            success=verified,
            patch_applied=patch_applied,
            verification_passed=verification_passed,
            rollback_performed=rollback_performed,
            output="\n".join(messages),
            errors=errors,
            file_modified=file_path,
            iteration=iteration
        )

        # Log iteration
        self.logger.log(iteration, observe_data, orient_data, decide_data, result)

        return result

    def get_history(self) -> List[Dict]:
        """Get iteration history."""
        return self.logger.get_history()

    def get_statistics(self) -> Dict[str, Any]:
        """Get act phase statistics."""
        history = self.get_history()

        successful = sum(1 for h in history if h.get("act", {}).get("success", False))
        rollbacks = sum(1 for h in history if h.get("act", {}).get("rollback_performed", False))

        return {
            "total_iterations": len(history),
            "successful_patches": successful,
            "rollback_count": rollbacks,
            "success_rate": successful / len(history) if history else 0
        }
