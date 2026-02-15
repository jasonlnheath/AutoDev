"""
Tests for Phase 2: Orient Phase

Tests context memory, pattern extraction, and similarity search.
"""
import sys
import unittest
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from byterover.local_context import (
    LocalContextTree,
    ContextNode,
    IterationRecord
)
from ooda.orient import PatternExtractor, Orienter


class TestPatternExtractor(unittest.TestCase):
    """Test pattern extraction from errors and fixes."""

    def test_extract_error_signature_syntax_error(self):
        """Test extracting signature from syntax error."""
        error = """File 'step0.py', line 42
    print('unclosed string
          ^
SyntaxError: EOL while scanning string literal"""
        sig = PatternExtractor.extract_error_signature(error)
        self.assertEqual(sig["error_type"], "SyntaxError")
        self.assertIn("step0.py", sig["location"])

    def test_extract_error_signature_name_error(self):
        """Test extracting signature from name error."""
        error = "NameError: name 'undefined_var' is not defined"
        sig = PatternExtractor.extract_error_signature(error)
        self.assertEqual(sig["error_type"], "NameError")
        self.assertIn("undefined_var", sig["message"])

    def test_extract_fix_pattern_addition(self):
        """Test detecting addition in diff."""
        patch = """--- a/file.py
+++ b/file.py
@@ -1,1 +1,2 @@
 def foo():
+    return 42"""
        pattern = PatternExtractor.extract_fix_pattern(patch)
        self.assertEqual(pattern["change_type"], "addition")
        self.assertEqual(pattern["added_lines"], 1)
        self.assertEqual(pattern["removed_lines"], 0)

    def test_extract_fix_pattern_modification(self):
        """Test detecting modification in diff."""
        patch = """--- a/file.py
+++ b/file.py
@@ -1,1 +1,1 @@
-x = 0
+x = 1"""
        pattern = PatternExtractor.extract_fix_pattern(patch)
        self.assertEqual(pattern["change_type"], "modification")
        self.assertEqual(pattern["total_changes"], 2)

    def test_generate_lesson_syntax_error(self):
        """Test lesson generation for syntax errors."""
        error = "SyntaxError: invalid syntax"
        fix = "+ print('hello')\n"
        lesson = PatternExtractor.generate_lesson(error, fix, True, 1)
        self.assertIn("Syntax error", lesson)

    def test_generate_lesson_no_success_no_lesson(self):
        """Test that failed fixes don't generate lessons."""
        error = "Error: something went wrong"
        fix = "- broken code\n"
        lesson = PatternExtractor.generate_lesson(error, fix, False, 1)
        self.assertIsNone(lesson)


class TestLocalContextTree(unittest.TestCase):
    """Test LocalContextTree persistence and queries."""

    def setUp(self):
        """Set up test context tree."""
        import tempfile
        self.temp_dir = Path(tempfile.mkdtemp())
        self.context = LocalContextTree(self.temp_dir)

    def tearDown(self):
        """Clean up temp directory."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_record_error_fix(self):
        """Test recording error-fix patterns."""
        self.context.record_error_fix(
            error="NameError: foo not defined",
            fix="+ foo = 42",
            file_path="test.py",
            success=True,
            iteration=1
        )
        self.assertEqual(len(self.context.patterns), 1)
        self.assertEqual(self.context.patterns[0]["error_type"], "name_error")

    def test_find_similar_errors(self):
        """Test finding similar errors."""
        self.context.record_error_fix(
            error="NameError: foo is not defined",
            fix="+ foo = 42",
            file_path="test.py",
            success=True,
            iteration=1
        )

        similar = self.context.find_similar_errors("NameError: bar not defined")
        self.assertGreater(len(similar), 0)
        self.assertGreater(similar[0]["similarity"], 0)

    def test_add_lesson(self):
        """Test adding lessons."""
        self.context.add_lesson("Always initialize variables")
        self.assertEqual(len(self.context.lessons), 1)

    def test_add_lesson_duplicate(self):
        """Test that duplicate lessons aren't added."""
        lesson = "Always check imports"
        self.context.add_lesson(lesson)
        self.context.add_lesson(lesson)
        self.assertEqual(len(self.context.lessons), 1)

    def test_get_statistics(self):
        """Test statistics gathering."""
        self.context.record_error_fix(
            error="Error 1",
            fix="fix 1",
            file_path="test.py",
            success=True,
            iteration=1
        )
        self.context.record_error_fix(
            error="Error 2",
            fix="fix 2",
            file_path="test.py",
            success=False,
            iteration=2
        )

        stats = self.context.get_statistics()
        self.assertEqual(stats["total_patterns"], 2)
        self.assertEqual(stats["successful_patterns"], 1)
        self.assertEqual(stats["failed_patterns"], 1)

    def test_error_classification(self):
        """Test error type classification."""
        self.context.record_error_fix(
            error="SyntaxError: invalid syntax",
            fix="fix",
            file_path="test.py",
            success=True,
            iteration=1
        )
        self.assertEqual(
            self.context.patterns[0]["error_type"],
            "syntax"
        )

    def test_persistence(self):
        """Test that context persists across instances."""
        # Create first instance and add data
        self.context.record_error_fix(
            error="Test error",
            fix="Test fix",
            file_path="test.py",
            success=True,
            iteration=1
        )

        # Create new instance - should load saved data
        context2 = LocalContextTree(self.temp_dir)
        self.assertEqual(len(context2.patterns), 1)


class TestOrienter(unittest.TestCase):
    """Test Orienter phase integration."""

    def setUp(self):
        """Set up test orienter."""
        import tempfile
        self.temp_dir = Path(tempfile.mkdtemp())
        self.orienter = Orienter(self.temp_dir)

    def tearDown(self):
        """Clean up temp directory."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_query_context_new(self):
        """Test querying context when empty."""
        context = self.orienter.query_context(
            error_message="Test error",
            file_path="test.py"
        )
        self.assertIn("similar_errors", context)
        self.assertIn("lessons_learned", context)
        self.assertIn("error_signature", context)

    def test_query_context_with_history(self):
        """Test querying context with existing patterns."""
        # Add some history
        self.orienter.record_result(
            error="NameError: x not defined",
            fix="+ x = 0",
            file_path="test.py",
            success=True,
            iteration=1
        )

        context = self.orienter.query_context(
            error_message="NameError: y not defined",
            file_path="test.py"
        )

        # Should find similar error
        self.assertGreater(len(context["similar_errors"]), 0)

    def test_record_result_and_lesson(self):
        """Test recording results generates lessons."""
        self.orienter.record_result(
            error="SyntaxError: invalid syntax",
            fix="+ print('fixed')",
            file_path="test.py",
            success=True,
            iteration=1
        )

        # Should have added a lesson
        lessons = self.orienter.get_lessons_learned()
        self.assertGreater(len(lessons), 0)

    def test_create_iteration_record(self):
        """Test creating full iteration record."""
        self.orienter.create_iteration_record(
            iteration=1,
            observe={"test": "data"},
            orient={"context": "info"},
            decide={"patch": "diff"},
            act={"applied": True},
            outcome="success"
        )

        stats = self.orienter.get_statistics()
        self.assertEqual(stats["total_iterations"], 1)

    def test_get_statistics(self):
        """Test getting statistics."""
        stats = self.orienter.get_statistics()
        self.assertIn("total_patterns", stats)
        self.assertIn("total_iterations", stats)
        self.assertIn("success_rate", stats)


def run_tests():
    """Run all Phase 2 tests."""
    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestPatternExtractor))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestLocalContextTree))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestOrienter))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
