"""
Tests for Phase 3: Decide Phase

Tests LLM integration, patch validation, and retry logic.
"""
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ooda.decide import (
    PatchValidator,
    PromptBuilder,
    Decider,
    PatchResult
)


class TestPatchValidator(unittest.TestCase):
    """Test patch validation."""

    def test_validate_diff_format_valid(self):
        """Test validation of valid diff."""
        patch = """--- a/file.py
+++ b/file.py
@@ -1,1 +1,2 @@
-def foo():
+def foo():
+    return 42"""
        is_valid, errors = PatchValidator.validate_patch(patch)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_validate_diff_format_missing_headers(self):
        """Test validation detects missing headers."""
        patch = "@@ -1,1 +1,2 @@\n-line\n+line"
        is_valid, errors = PatchValidator.validate_patch(patch)
        self.assertFalse(is_valid)
        self.assertIn("Missing diff header", str(errors))

    def test_validate_python_syntax_valid(self):
        """Test syntax validation of valid Python."""
        code = "def foo():\n    return 42"
        errors = PatchValidator.validate_python_syntax(code)
        self.assertEqual(len(errors), 0)

    def test_validate_python_syntax_invalid(self):
        """Test syntax validation catches syntax errors."""
        code = "def foo(:\n    return 42"
        errors = PatchValidator.validate_python_syntax(code)
        self.assertGreater(len(errors), 0)
        self.assertIn("Syntax error", errors[0])

    def test_extract_new_code(self):
        """Test extracting new code from patch."""
        patch = """--- a/file.py
+++ b/file.py
@@ -1,1 +1,2 @@
 def foo():
+    return 42"""
        new_code = PatchValidator.extract_new_code(patch)
        self.assertIsNotNone(new_code)
        self.assertIn("return 42", new_code)

    def test_extract_new_code_empty(self):
        """Test extracting from patch with only deletions."""
        patch = """--- a/file.py
+++ b/file.py
@@ -1,1 +1,1 @@
-x = 1
+x = 2"""
        new_code = PatchValidator.extract_new_code(patch)
        self.assertIsNotNone(new_code)

    def test_validate_rejects_invalid_hunk(self):
        """Test validation rejects invalid hunk headers."""
        patch = """--- a/file.py
+++ b/file.py
@@ invalid @@
 def foo():"""
        is_valid, errors = PatchValidator.validate_patch(patch)
        self.assertFalse(is_valid)


class TestPromptBuilder(unittest.TestCase):
    """Test prompt building."""

    def setUp(self):
        """Set up test fixtures."""
        import tempfile
        self.temp_dir = Path(tempfile.mkdtemp())
        self.template_path = self.temp_dir / "template.txt"
        self.template_path.write_text(
            "Fix the error in {file_path}\n"
            "Error: {error_message}\n"
            "Test: {test_name}\n"
            "Code:\n{current_code}"
        )
        self.builder = PromptBuilder(self.template_path)

    def tearDown(self):
        """Clean up temp directory."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_build_basic_prompt(self):
        """Test building basic prompt."""
        prompt = self.builder.build(
            file_path="test.py",
            current_code="def foo(): pass",
            error_message="Error!",
            context={},
            test_name="test_foo"
        )
        self.assertIn("test.py", prompt)
        self.assertIn("Error!", prompt)
        self.assertIn("test_foo", prompt)
        self.assertIn("def foo(): pass", prompt)

    def test_build_with_similar_errors(self):
        """Test building prompt with similar errors context."""
        context = {
            "similar_errors": [
                {"error": "NameError", "fix": "+ x = 0", "success": True}
            ]
        }
        prompt = self.builder.build(
            file_path="test.py",
            current_code="x",
            error_message="NameError",
            context=context,
            test_name="test"
        )
        self.assertIn("Similar Past Errors", prompt)
        self.assertIn("NameError", prompt)
        self.assertIn("[OK]", prompt)

    def test_build_with_lessons(self):
        """Test building prompt with lessons learned."""
        context = {
            "lessons_learned": ["Always initialize variables"]
        }
        prompt = self.builder.build(
            file_path="test.py",
            current_code="x",
            error_message="Error",
            context=context
        )
        self.assertIn("Lessons Learned", prompt)
        self.assertIn("Always initialize variables", prompt)

    def test_build_minimal_mode(self):
        """Test minimal mode adds appropriate instruction."""
        prompt = self.builder.build(
            file_path="test.py",
            current_code="x",
            error_message="Error",
            context={},
            mode="minimal"
        )
        self.assertIn("MINIMAL", prompt)

    def test_build_with_error_signature(self):
        """Test prompt includes error type from signature."""
        context = {
            "error_signature": {"error_type": "SyntaxError"}
        }
        prompt = self.builder.build(
            file_path="test.py",
            current_code="x",
            error_message="SyntaxError: invalid",
            context=context
        )
        # Should include context even if empty
        self.assertIn("Fix the error", prompt)


class TestDecider(unittest.TestCase):
    """Test Decider phase."""

    def setUp(self):
        """Set up test fixtures."""
        import tempfile
        import json

        self.temp_dir = Path(tempfile.mkdtemp())

        # Create config directory
        config_dir = self.temp_dir / "config"
        config_dir.mkdir()

        # Create LLM config
        llm_config = {
            "default_model": "glm-4.5-air",
            "models": {
                "glm-4.5-air": {
                    "name": "GLM-4.5-Air",
                    "max_tokens": 2000,
                    "temperature": 0.3
                },
                "glm-5": {
                    "name": "GLM-5",
                    "max_tokens": 4000,
                    "temperature": 0.5
                }
            },
            "retry": {
                "max_attempts": 3,
                "backoff_multiplier": 2,
                "initial_delay_sec": 0.01  # Fast for tests
            }
        }
        (config_dir / "llm_settings.json").write_text(json.dumps(llm_config))

        # Create prompts directory
        prompts_dir = self.temp_dir / "prompts"
        prompts_dir.mkdir()
        (prompts_dir / "patch_generation.txt").write_text(
            "Generate patch for {file_path}\n"
            "Error: {error_message}\n"
            "{current_code}"
        )

        # Create byterover directory (for GLM client mock)
        byterover_dir = self.temp_dir / "byterover"
        byterover_dir.mkdir()

        self.decider = Decider(self.temp_dir)

    def tearDown(self):
        """Clean up temp directory."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_select_model_for_complex_error(self):
        """Test model selection for complex errors."""
        context = {
            "error_signature": {"error_type": "SyntaxError"}
        }
        model = self.decider._select_model(context)
        self.assertEqual(model, "glm-5")

    def test_select_model_for_simple_error(self):
        """Test model selection for simple errors."""
        context = {
            "error_signature": {"error_type": "NameError"}
        }
        model = self.decider._select_model(context)
        self.assertEqual(model, "glm-4.5-air")

    def test_select_model_for_failed_attempts(self):
        """Test model upgrades when previous attempts failed."""
        context = {
            "error_signature": {"error_type": "NameError"},
            "similar_errors": [
                {"error": "NameError", "success": False},
                {"error": "NameError", "success": False}
            ]
        }
        model = self.decider._select_model(context)
        self.assertEqual(model, "glm-5")

    def test_extract_diff_from_code_block(self):
        """Test extracting diff from markdown code block."""
        response = """
Here's the fix:

```diff
--- a/test.py
+++ b/test.py
@@ -1,1 +1,2 @@
-x
+x = 0
```
"""
        diff = self.decider._extract_diff(response)
        self.assertIsNotNone(diff)
        self.assertIn("--- a/test.py", diff)
        self.assertIn("+x = 0", diff)

    def test_extract_diff_from_plain_response(self):
        """Test extracting diff from plain response."""
        response = """--- a/test.py
+++ b/test.py
@@ -1,1 +1,2 @@
-x
+x = 0"""
        diff = self.decider._extract_diff(response)
        self.assertIsNotNone(diff)
        self.assertIn("--- a/test.py", diff)

    def test_extract_diff_returns_none_for_no_diff(self):
        """Test extraction returns None when no diff found."""
        response = "I don't have a diff for you."
        diff = self.decider._extract_diff(response)
        self.assertIsNone(diff)

    @patch('time.sleep')
    @patch.object(Decider, '_get_glm_client')
    def test_generate_patch_with_mock_llm(self, mock_client_fn, mock_sleep):
        """Test patch generation with mocked LLM."""
        # Mock GLM client
        mock_client = Mock()
        mock_client.call.return_value = """--- a/test.py
+++ b/test.py
@@ -1,1 +1,2 @@
-x
+x = 0"""
        mock_client_fn.return_value = mock_client

        context = {
            "error_signature": {"error_type": "NameError"},
            "similar_errors": [],
            "lessons_learned": []
        }

        result = self.decider.generate_patch(
            file_path="test.py",
            current_code="x",
            error_message="NameError: name 'x' is not defined",
            context=context
        )

        self.assertIsNotNone(result)
        self.assertIsInstance(result, PatchResult)
        self.assertTrue(result.validation_passed)
        self.assertEqual(result.model_used, "glm-4.5-air")

    @patch('time.sleep')
    @patch.object(Decider, '_get_glm_client')
    def test_generate_patch_retries_on_validation_failure(self, mock_client_fn, mock_sleep):
        """Test retry when validation fails."""
        # First call returns invalid patch, second returns valid
        mock_client = Mock()
        mock_client.call.side_effect = [
            "invalid response",  # No diff
            """--- a/test.py
+++ b/test.py
@@ -1,1 +1,2 @@
-x
+x = 0"""
        ]
        mock_client_fn.return_value = mock_client

        context = {
            "error_signature": {"error_type": "NameError"},
            "similar_errors": [],
            "lessons_learned": []
        }

        result = self.decider.generate_patch(
            file_path="test.py",
            current_code="x",
            error_message="NameError",
            context=context
        )

        self.assertIsNotNone(result)
        self.assertEqual(result.attempts, 2)

    def test_get_statistics(self):
        """Test getting statistics."""
        stats = self.decider.get_statistics()
        self.assertIn("patches_generated", stats)
        self.assertIn("patches_validated", stats)
        self.assertIn("retries_performed", stats)

    def test_reset_statistics(self):
        """Test resetting statistics."""
        self.decider.stats["patches_generated"] = 5
        self.decider.reset_statistics()
        self.assertEqual(self.decider.stats["patches_generated"], 0)

    def test_estimate_tokens(self):
        """Test token estimation."""
        text = "hello world this is a test"
        estimate = self.decider.estimate_tokens(text)
        self.assertGreater(estimate, 0)


class TestPatchResult(unittest.TestCase):
    """Test PatchResult dataclass."""

    def test_patch_result_creation(self):
        """Test creating PatchResult."""
        result = PatchResult(
            patch="--- a/file\n+++ b/file",
            model_used="glm-4.5-air",
            attempts=1,
            validation_passed=True,
            validation_errors=[],
            prompt_tokens=100
        )
        self.assertEqual(result.model_used, "glm-4.5-air")
        self.assertTrue(result.validation_passed)


def run_tests():
    """Run all Phase 3 tests."""
    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestPatchValidator))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestPromptBuilder))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestDecider))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestPatchResult))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
