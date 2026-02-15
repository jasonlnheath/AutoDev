"""
Tests for Phase 4: Act Phase

Tests diff application, rollback, verification, and logging.
"""
import sys
import unittest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ooda.act import (
    DiffParser,
    DiffApplier,
    VerificationSuite,
    IterationLogger,
    Actor,
    ActResult,
    DiffHunk,
    ParsedDiff
)


class TestDiffParser(unittest.TestCase):
    """Test unified diff parsing."""

    def test_parse_simple_diff(self):
        """Test parsing a simple diff."""
        diff = """--- a/file.py
+++ b/file.py
@@ -1,1 +1,2 @@
-x
+x = 0"""
        parsed = DiffParser.parse(diff)

        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.old_file, "file.py")
        self.assertEqual(parsed.new_file, "file.py")
        self.assertEqual(len(parsed.hunks), 1)

    def test_parse_multi_hunk_diff(self):
        """Test parsing a diff with multiple hunks."""
        diff = """--- a/file.py
+++ b/file.py
@@ -1,3 +1,3 @@
-x
-y
+x
+y
@@ -10,2 +10,2 @@
-old_line
+new_line"""
        parsed = DiffParser.parse(diff)

        self.assertIsNotNone(parsed)
        self.assertEqual(len(parsed.hunks), 2)

    def test_parse_with_context_lines(self):
        """Test parsing diff with context lines."""
        diff = """--- a/file.py
+++ b/file.py
@@ -1,3 +1,3 @@
 def foo():
-    return 1
+    return 2
     pass"""
        parsed = DiffParser.parse(diff)

        self.assertIsNotNone(parsed)
        hunk = parsed.hunks[0]
        # Should have context lines (starting with space)
        context_lines = [l for l in hunk.lines if l.startswith(' ')]
        self.assertGreater(len(context_lines), 0)

    def test_parse_invalid_diff_returns_none(self):
        """Test that invalid diff returns None."""
        diff = "This is not a valid diff"
        parsed = DiffParser.parse(diff)
        self.assertIsNone(parsed)

    def test_parse_hunk_counts(self):
        """Test hunk count parsing."""
        diff = """--- a/file.py
+++ b/file.py
@@ -1,5 +1,5 @@
 line1
 line2"""
        parsed = DiffParser.parse(diff)

        self.assertIsNotNone(parsed)
        hunk = parsed.hunks[0]
        self.assertEqual(hunk.old_start, 1)
        self.assertEqual(hunk.old_count, 5)
        self.assertEqual(hunk.new_start, 1)
        self.assertEqual(hunk.new_count, 5)


class TestDiffApplier(unittest.TestCase):
    """Test diff application."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.applier = DiffApplier(self.temp_dir)

        # Create test file
        self.test_file = self.temp_dir / "test.py"
        self.test_file.write_text("line1\nline2\nline3\n")

    def tearDown(self):
        """Clean up temp directory."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_apply_simple_addition(self):
        """Test applying a simple addition diff."""
        diff = """--- a/test.py
+++ b/test.py
@@ -1,3 +1,4 @@
 line1
+new_line
 line2
 line3"""

        success, error = self.applier.apply(diff, "test.py")
        self.assertTrue(success)
        self.assertIsNone(error)

        result = self.test_file.read_text()
        self.assertIn("new_line", result)
        self.assertIn("line1", result)

    def test_apply_simple_removal(self):
        """Test applying a simple removal diff."""
        diff = """--- a/test.py
+++ b/test.py
@@ -1,3 +1,2 @@
 line1
-line2
 line3"""

        success, error = self.applier.apply(diff, "test.py")
        self.assertTrue(success)

        result = self.test_file.read_text()
        self.assertNotIn("line2", result)
        self.assertIn("line1", result)
        self.assertIn("line3", result)

    def test_apply_modification(self):
        """Test applying a modification diff."""
        diff = """--- a/test.py
+++ b/test.py
@@ -1,3 +1,3 @@
 line1
-line2
+line2_modified
 line3"""

        success, error = self.applier.apply(diff, "test.py")
        self.assertTrue(success)

        result = self.test_file.read_text()
        self.assertIn("line2_modified", result)
        # Check exact expected content
        self.assertEqual(result.strip(), "line1\nline2_modified\nline3")

    def test_apply_returns_error_on_mismatch(self):
        """Test that mismatch returns error."""
        diff = """--- a/test.py
+++ b/test.py
@@ -1,3 +1,3 @@
 wrong_line
-line2
+line2_modified
 line3"""

        success, error = self.applier.apply(diff, "test.py")
        self.assertFalse(success)
        self.assertIsNotNone(error)
        self.assertIn("mismatch", error.lower())

    def test_apply_nonexistent_file(self):
        """Test applying diff to nonexistent file."""
        diff = """--- a/missing.py
+++ b/missing.py
@@ -0,0 +1,1 @@
+new"""

        success, error = self.applier.apply(diff, "missing.py")
        self.assertFalse(success)
        self.assertIn("not found", error.lower())


class TestVerificationSuite(unittest.TestCase):
    """Test verification suite."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.target_dir = self.temp_dir / "mal"
        self.target_dir.mkdir()

        self.verifier = VerificationSuite(self.temp_dir, "mal")

    def tearDown(self):
        """Clean up temp directory."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_check_syntax_valid(self):
        """Test syntax check with valid code."""
        test_file = self.target_dir / "test.py"
        test_file.write_text("def foo():\n    return 42\n")

        valid, msg = self.verifier.check_syntax("test.py")
        self.assertTrue(valid)
        self.assertIn("Valid", msg)

    def test_check_syntax_invalid(self):
        """Test syntax check with invalid code."""
        test_file = self.target_dir / "test.py"
        test_file.write_text("def foo(:\n    return 42\n")

        valid, msg = self.verifier.check_syntax("test.py")
        self.assertFalse(valid)
        # Error message includes "invalid syntax"
        self.assertIn("syntax", msg.lower())

    def test_check_import_valid(self):
        """Test import check with valid code."""
        test_file = self.target_dir / "test.py"
        test_file.write_text("x = 42\n")

        valid, msg = self.verifier.check_import("test.py")
        self.assertTrue(valid)
        self.assertIn("compiles", msg)

    def test_verify_all_passing(self):
        """Test full verification with passing code."""
        test_file = self.target_dir / "test.py"
        test_file.write_text("def foo():\n    return 42\n")

        passed, messages = self.verifier.verify_all("test.py")
        self.assertTrue(passed)
        self.assertGreater(len(messages), 0)

    def test_verify_all_failing_syntax(self):
        """Test full verification with syntax error."""
        test_file = self.target_dir / "test.py"
        test_file.write_text("def foo(:\n    pass\n")

        passed, messages = self.verifier.verify_all("test.py")
        self.assertFalse(passed)
        self.assertIn("[FAIL]", str(messages))

    def test_run_tests(self):
        """Test running test suite (compilation check)."""
        # Create multiple files
        (self.target_dir / "file1.py").write_text("x = 1")
        (self.target_dir / "file2.py").write_text("y = 2")
        (self.target_dir / "_skip.py").write_text("z = 3")

        passed, msg = self.verifier.run_tests()
        self.assertTrue(passed)
        # Message contains "compile"
        self.assertIn("compile", msg.lower())


class TestIterationLogger(unittest.TestCase):
    """Test iteration logging."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.logs_dir = self.temp_dir / "logs"
        self.logger = IterationLogger(self.logs_dir)

    def tearDown(self):
        """Clean up temp directory."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_log_iteration(self):
        """Test logging an iteration."""
        result = ActResult(
            success=True,
            patch_applied=True,
            verification_passed=True,
            rollback_performed=False,
            output="All good",
            errors=[],
            file_modified="test.py",
            iteration=1
        )

        self.logger.log(
            iteration=1,
            observe_data={"test": "data"},
            orient_data={"context": "info"},
            decide_data={"patch": "diff"},
            act_result=result
        )

        history = self.logger.get_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["iteration"], 1)

    def test_log_updates_summary(self):
        """Test that logging updates summary."""
        result = ActResult(
            success=True,
            patch_applied=True,
            verification_passed=True,
            rollback_performed=False,
            output="",
            errors=[],
            file_modified="test.py",
            iteration=1
        )

        self.logger.log(1, {}, {}, {}, result)

        summary_file = self.logs_dir / "summary.json"
        self.assertTrue(summary_file.exists())

        import json
        summary = json.loads(summary_file.read_text())
        self.assertEqual(summary["total_iterations"], 1)
        self.assertEqual(summary["successful_iterations"], 1)

    def test_log_failed_iteration(self):
        """Test logging failed iteration."""
        result = ActResult(
            success=False,
            patch_applied=False,
            verification_passed=False,
            rollback_performed=True,
            output="",
            errors=["Error message"],
            file_modified="test.py",
            iteration=1
        )

        self.logger.log(1, {}, {}, {}, result)

        history = self.logger.get_history()
        self.assertEqual(history[0]["act"]["success"], False)
        self.assertEqual(history[0]["act"]["errors"], ["Error message"])


class TestActor(unittest.TestCase):
    """Test Actor integration."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.mal_dir = self.temp_dir / "mal"
        self.mal_dir.mkdir()

        # Create test file
        self.test_file = self.mal_dir / "test.py"
        self.test_file.write_text("x = 1\ny = 2\n")

        self.actor = Actor(self.temp_dir, "mal")

    def tearDown(self):
        """Clean up temp directory."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_act_successful_patch(self):
        """Test successful patch application and verification."""
        diff = """--- a/test.py
+++ b/test.py
@@ -1,2 +1,2 @@
-x = 1
+x = 10"""

        result = self.actor.act("test.py", diff, 1)

        self.assertTrue(result.success)
        self.assertTrue(result.patch_applied)
        self.assertTrue(result.verification_passed)
        self.assertFalse(result.rollback_performed)

        # Verify file was modified
        content = self.test_file.read_text()
        self.assertIn("x = 10", content)

    def test_act_creates_backup(self):
        """Test that backup is created."""
        diff = """--- a/test.py
+++ b/test.py
@@ -1,2 +1,2 @@
-x = 1
+x = 10"""

        self.actor.act("test.py", diff, 1)

        # Check backup exists
        self.assertIn("test.py", self.actor.backups)
        self.assertTrue(self.actor.backups["test.py"].exists())

    def test_act_rollback_on_syntax_error(self):
        """Test rollback when patch introduces syntax error."""
        diff = """--- a/test.py
+++ b/test.py
@@ -1,2 +1,2 @@
-x = 1
+def foo(:"""

        result = self.actor.act("test.py", diff, 1)

        self.assertFalse(result.success)
        self.assertTrue(result.patch_applied)
        self.assertFalse(result.verification_passed)
        self.assertTrue(result.rollback_performed)

        # Verify file was restored
        content = self.test_file.read_text()
        self.assertIn("x = 1", content)
        self.assertNotIn("def foo(:", content)

    def test_act_with_full_data(self):
        """Test act with full observe/orient/decide data."""
        diff = """--- a/test.py
+++ b/test.py
@@ -1,2 +1,2 @@
-x = 1
+x = 10"""

        observe_data = {"test_output": "..."}
        orient_data = {"similar_errors": []}
        decide_data = {"model": "glm-4.5-air"}

        result = self.actor.act(
            "test.py",
            diff,
            1,
            observe_data=observe_data,
            orient_data=orient_data,
            decide_data=decide_data
        )

        self.assertTrue(result.success)

        # Check logged data
        history = self.actor.get_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["observe"], observe_data)
        self.assertEqual(history[0]["orient"], orient_data)
        self.assertEqual(history[0]["decide"], decide_data)

    def test_get_statistics(self):
        """Test getting actor statistics."""
        diff = """--- a/test.py
+++ b/test.py
@@ -1,2 +1,2 @@
-x = 1
+x = 10"""

        self.actor.act("test.py", diff, 1)

        stats = self.actor.get_statistics()
        self.assertEqual(stats["total_iterations"], 1)
        self.assertEqual(stats["successful_patches"], 1)


class TestActResult(unittest.TestCase):
    """Test ActResult dataclass."""

    def test_act_result_creation(self):
        """Test creating ActResult."""
        result = ActResult(
            success=True,
            patch_applied=True,
            verification_passed=True,
            rollback_performed=False,
            output="Success",
            errors=[],
            file_modified="test.py",
            iteration=1
        )

        self.assertTrue(result.success)
        self.assertEqual(result.iteration, 1)


def run_tests():
    """Run all Phase 4 tests."""
    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestDiffParser))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestDiffApplier))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestVerificationSuite))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestIterationLogger))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestActor))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestActResult))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
