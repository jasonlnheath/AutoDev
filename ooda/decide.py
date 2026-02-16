"""
DECIDE Phase: Generate code patches using LLM.

Use context from orient phase to generate appropriate fixes.
Enhanced with validation, retry logic, and fallback strategies.
"""
import json
import re
import time
import ast
import subprocess
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass


@dataclass
class PatchResult:
    """Result of patch generation."""
    patch: str
    model_used: str
    attempts: int
    validation_passed: bool
    validation_errors: List[str]
    prompt_tokens: int


class PatchValidator:
    """Validate generated patches for syntax and correctness."""

    @staticmethod
    def validate_diff_format(patch: str) -> List[str]:
        """Validate unified diff format."""
        errors = []

        # Check for required diff markers
        if "--- a/" not in patch:
            errors.append("Missing diff header: --- a/")
        if "+++ b/" not in patch:
            errors.append("Missing diff header: +++ b/")
        if "@@" not in patch:
            errors.append("Missing hunk markers: @@")

        # Check for valid diff lines
        lines = patch.split('\n')
        for i, line in enumerate(lines):
            if line.startswith('@@') and not line.endswith('@@'):
                # Hunk header should be like @@ -1,1 +1,1 @@
                if not re.match(r'^@@\s+-\d+,\d+\s+\+\d+,\d+\s+@@', line):
                    errors.append(f"Invalid hunk format at line {i}: {line}")

        return errors

    @staticmethod
    def validate_python_syntax(code: str) -> List[str]:
        """Validate Python syntax."""
        errors = []
        try:
            ast.parse(code)
        except SyntaxError as e:
            errors.append(f"Syntax error: {e.msg} at line {e.lineno}")
        return errors

    @staticmethod
    def extract_new_code(patch: str) -> Optional[str]:
        """Extract new code from patch for syntax validation."""
        lines = patch.split('\n')
        new_lines = []

        for line in lines:
            if line.startswith('+') and not line.startswith('+++'):
                new_lines.append(line[1:])
            elif line.startswith(' ') and not line.startswith('---'):
                # Context lines (unchanged)
                new_lines.append(line[1:])

        if not new_lines:
            return None

        return '\n'.join(new_lines)

    @staticmethod
    def validate_patch(patch: str) -> tuple[bool, List[str]]:
        """
        Full patch validation.

        Returns (is_valid, list_of_errors)
        """
        errors = []

        # Check format
        errors.extend(PatchValidator.validate_diff_format(patch))

        # Check syntax of new code
        new_code = PatchValidator.extract_new_code(patch)
        if new_code:
            errors.extend(PatchValidator.validate_python_syntax(new_code))

        return len(errors) == 0, errors


class PromptBuilder:
    """Build prompts for LLM patch generation."""

    def __init__(self, template_path: Path, use_mal_template: bool = False):
        self.template_path = template_path
        self.use_mal_template = use_mal_template
        self.base_template = template_path.read_text()

    def build(
        self,
        file_path: str,
        current_code: str,
        error_message: str,
        context: Dict[str, Any],
        test_name: str = "",
        mode: str = "standard",
        missing_functions: List[str] = None,
        current_step: int = None
    ) -> str:
        """
        Build prompt from template and context.

        Args:
            file_path: Path to file to patch
            current_code: Current file contents
            error_message: Error message to fix
            context: Context from orient phase
            test_name: Name of failing test
            mode: Prompt mode (standard, minimal, detailed)
            missing_functions: List of missing function names
            current_step: Current Mal step number
        """
        # Build context section
        context_section = self._build_context_section(context, mode)

        # For Mal-specific template, build the prompt manually
        # since the template has different placeholders
        if "mal_patch_generation" in str(self.template_path):
            missing_str = ", ".join(missing_functions or []) or "none"
            step_str = str(current_step or "unknown")

            prompt = f"""You are an expert Mal Lisp implementer. Given a failing test and error, generate a minimal patch.

## Context
- File: {file_path}
- Error: Tests are failing for missing functions: {missing_str}
- Failing Test: {test_name or "(unknown)"}
- Current Step: {step_str}

## Current Code
```python
{current_code[:3000]}
```

## Task
Generate a MINIMAL patch that adds the missing functions to make tests pass.

{context_section}

## Output Format
Return ONLY a diff in unified format:
```diff
--- a/{file_path}
+++ b/{file_path}
@@ -1,1 +1,1 @@
-old line
+new line
```
"""
        else:
            # Use generic template
            prompt = self.base_template.format(
                file_path=file_path,
                error_message=error_message,
                test_name=test_name or "(unknown test)",
                current_code=current_code
            )
            prompt += context_section

        # Add mode-specific instructions
        if mode == "minimal":
            prompt += "\n\nIMPORTANT: Make the MINIMAL change necessary. Do not refactor."
        elif mode == "detailed":
            prompt += "\n\nPlease explain your reasoning after the diff."

        return prompt

    def _build_context_section(self, context: Dict[str, Any], mode: str) -> str:
        """Build the context section of the prompt."""
        section = ""

        # Similar errors
        similar = context.get("similar_errors", [])[:3]  # Top 3
        if similar:
            section += "\n## Similar Past Errors and Their Fixes\n"
            for i, err in enumerate(similar, 1):
                section += f"\n{i}) Error Type: {err.get('error_type', 'unknown')}\n"
                section += f"   Error: {err['error'][:100]}...\n"
                section += f"   Fix: {err['fix'][:150]}...\n"
                if err.get('success'):
                    section += "   Status: [OK] This fix worked\n"
                else:
                    section += "   Status: [FAIL] This fix failed\n"

        # File history
        history = context.get("file_history", [])[:3]
        if history:
            section += "\n## File Change History\n"
            for h in history:
                section += f"- Iteration {h['iteration']}: {h['outcome']}\n"

        # Lessons learned
        lessons = context.get("lessons_learned", [])[:5]
        if lessons:
            section += "\n## Lessons Learned from Previous Iterations\n"
            for lesson in lessons:
                section += f"- {lesson}\n"

        # Suggestion from orient
        suggestion = context.get("suggestion", "")
        if suggestion:
            section += f"\n## Suggestion\n{suggestion}\n"

        return section


class Decider:
    """
    Decide: Generate patches using GLM LLM with retry and validation.

    Features:
    - Retry with exponential backoff
    - Model selection (Air for simple, 5 for complex)
    - Patch validation before returning
    - Fallback strategies
    """

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.byterover_dir = project_root / "byterover"
        self.config_path = project_root / "config" / "llm_settings.json"
        self.prompt_template_path = project_root / "prompts" / "patch_generation.txt"

        # Load configuration
        self.config = json.loads(self.config_path.read_text())

        # Initialize components
        self.prompt_builder = PromptBuilder(self.prompt_template_path, use_mal_template=True)
        self.validator = PatchValidator()

        # Statistics
        self.stats = {
            "patches_generated": 0,
            "patches_validated": 0,
            "retries_performed": 0,
            "fallbacks_used": 0
        }

    def _get_llm_client(self):
        """Get LLM client from byterover (supports GLM, OpenAI, Anthropic, etc)."""
        import sys
        sys.path.insert(0, str(self.byterover_dir))
        from llm_client import create_llm_client
        return create_llm_client()

    def _select_model(self, context: Dict[str, Any]) -> str:
        """
        Select appropriate model based on context.

        Returns model name (glm-4.7 for code generation).
        """
        # GLM-4.5-Air produces garbage output for code patches
        # GLM-4.7 is reliable for code generation
        return "glm-4.7"

    def generate_patch(
        self,
        file_path: str,
        current_code: str,
        error_message: str,
        context: Dict[str, Any],
        test_name: str = "",
        max_attempts: Optional[int] = None,
        missing_functions: List[str] = None,
        current_step: int = None
    ) -> Optional[PatchResult]:
        """
        Generate a patch using LLM with context from orient phase.

        Args:
            file_path: Path to file to patch
            current_code: Current file contents
            error_message: Error message to fix
            context: Context from orient phase
            test_name: Name of failing test
            max_attempts: Max retry attempts (default from config)
            missing_functions: List of missing function names
            current_step: Current Mal step number

        Returns: PatchResult or None if all attempts failed
        """
        max_attempts = max_attempts or self.config["retry"]["max_attempts"]

        for attempt in range(1, max_attempts + 1):
            print(f"  Attempt {attempt}/{max_attempts}...")

            # Select model based on context
            model = self._select_model(context)

            # Build prompt with Mal-specific context
            prompt = self.prompt_builder.build(
                file_path=file_path,
                current_code=current_code,
                error_message=error_message,
                context=context,
                test_name=test_name,
                mode="minimal" if attempt > 1 else "standard",
                missing_functions=missing_functions,
                current_step=current_step
            )

            # Call LLM
            try:
                client = self._get_llm_client()
                response = client.call(
                    prompt=prompt,
                    model=model,
                    max_tokens=self.config["models"][model]["max_tokens"],
                    temperature=self.config["models"][model]["temperature"]
                )
            except Exception as e:
                print(f"    LLM call failed: {e}")
                if attempt < max_attempts:
                    self._backoff(attempt)
                    continue
                return None

            # Extract diff
            patch = self._extract_diff(response)
            if not patch:
                print(f"    No diff in response")
                if attempt < max_attempts:
                    self._backoff(attempt)
                    continue
                return None

            # Validate patch
            is_valid, errors = self.validator.validate_patch(patch)

            # Additional check: ensure patch actually adds code
            if is_valid:
                # Check if patch adds actual code (not just comments/whitespace)
                code_added = False
                for line in patch.split('\n'):
                    if line.startswith('+') and not line.startswith('+++'):
                        content = line[1:].strip()
                        # Skip empty lines, whitespace-only, and comment-only lines
                        if content and not content.startswith('#'):
                            code_added = True
                            break

                if not code_added:
                    print(f"    [FAIL] Patch doesn't add any actual code")
                    is_valid = False
                    errors.append("No code added")

            if is_valid:
                print(f"    [OK] Patch validated")
                self.stats["patches_generated"] += 1
                self.stats["patches_validated"] += 1

                return PatchResult(
                    patch=patch,
                    model_used=model,
                    attempts=attempt,
                    validation_passed=True,
                    validation_errors=[],
                    prompt_tokens=len(prompt.split())
                )
            else:
                print(f"    [FAIL] Validation failed: {errors[0]}")
                self.stats["retries_performed"] += 1

                if attempt < max_attempts:
                    self._backoff(attempt)

        # All attempts failed
        return None

    def _extract_diff(self, response: str) -> Optional[str]:
        """
        Extract unified diff from LLM response.

        Handles various response formats.
        """
        response = response.strip()

        # Method 1: Look for diff in code blocks
        code_block_pattern = r'```(?:diff)?\n(.*?)```'
        matches = re.findall(code_block_pattern, response, re.DOTALL)
        for match in matches:
            if "--- a/" in match:
                return match.strip()

        # Method 2: Look for diff markers directly
        if "--- a/" in response:
            lines = response.split('\n')
            diff_lines = []
            in_diff = False

            for line in lines:
                if line.startswith("--- a/"):
                    in_diff = True
                if in_diff:
                    diff_lines.append(line)
                    # End of diff (start of new section)
                    if line.strip() and not line.startswith(('---', '+++', '@@', '+', '-', ' ')):
                        break

            return '\n'.join(diff_lines).strip()

        # Method 3: Response might just be the diff
        if any(marker in response for marker in ["--- a/", "+++ b/", "@@"]):
            return response

        return None

    def _backoff(self, attempt: int):
        """Exponential backoff before retry."""
        delay = self.config["retry"]["initial_delay_sec"]
        multiplier = self.config["retry"]["backoff_multiplier"]
        wait_time = delay * (multiplier ** (attempt - 1))
        print(f"    Waiting {wait_time}s before retry...")
        time.sleep(wait_time)

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough approximation)."""
        return len(text.split()) * 1.3  # Rough estimate

    def get_statistics(self) -> Dict[str, Any]:
        """Get generation statistics."""
        return self.stats.copy()

    def reset_statistics(self):
        """Reset statistics."""
        self.stats = {
            "patches_generated": 0,
            "patches_validated": 0,
            "retries_performed": 0,
            "fallbacks_used": 0
        }
