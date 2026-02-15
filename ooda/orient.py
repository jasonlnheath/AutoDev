"""
ORIENT Phase: Query context memory for relevant patterns.

Learn from previous iterations to avoid repeating mistakes.
Enhanced with LocalContextTree for better pattern matching.
"""
import sys
from pathlib import Path
from typing import List, Dict, Optional, Any

# Import LocalContextTree from byterover
sys.path.insert(0, str(Path(__file__).parent.parent / "byterover"))
from local_context import LocalContextTree, ContextNode, IterationRecord


class PatternExtractor:
    """Extract patterns from code changes and errors."""

    @staticmethod
    def extract_error_signature(error: str) -> Dict[str, str]:
        """
        Extract structured error signature for matching.

        Returns dict with error_type, location, message components.
        """
        lines = error.strip().split('\n')
        first_line = lines[0] if lines else ""

        # Parse common Python error formats
        # e.g., "File 'step0.py', line 42, in <module>"
        location = ""
        error_type = ""
        message = ""

        for line in lines[:5]:  # Check first few lines
            if "File " in line and "line " in line:
                location = line.strip()
            elif "Error" in line or "Exception" in line:
                parts = line.split(":")
                if len(parts) >= 2:
                    error_type = parts[0].strip()
                    message = ":".join(parts[1:]).strip()

        return {
            "error_type": error_type or "UnknownError",
            "location": location,
            "message": message or first_line,
            "raw": error
        }

    @staticmethod
    def extract_fix_pattern(patch: str) -> Dict[str, Any]:
        """
        Extract fix pattern from a diff.

        Returns dict with change_type, lines_changed, etc.
        """
        lines = patch.split('\n')

        added_lines = []
        removed_lines = []
        file_path = ""

        for line in lines:
            if line.startswith("--- a/"):
                file_path = line[6:]
            elif line.startswith("+") and not line.startswith("+++"):
                added_lines.append(line[1:])
            elif line.startswith("-") and not line.startswith("---"):
                removed_lines.append(line[1:])

        # Classify change type
        change_type = "unknown"
        if added_lines and not removed_lines:
            change_type = "addition"
        elif removed_lines and not added_lines:
            change_type = "deletion"
        elif added_lines and removed_lines:
            change_type = "modification"

        return {
            "file": file_path,
            "change_type": change_type,
            "added_lines": len(added_lines),
            "removed_lines": len(removed_lines),
            "total_changes": len(added_lines) + len(removed_lines)
        }

    @staticmethod
    def generate_lesson(
        error: str,
        fix: str,
        success: bool,
        iteration: int
    ) -> Optional[str]:
        """
        Generate a lesson learned from an error-fix pair.

        Returns human-readable lesson or None if no clear lesson.
        """
        if not success:
            return None

        error_sig = PatternExtractor.extract_error_signature(error)
        fix_pattern = PatternExtractor.extract_fix_pattern(fix)

        error_type = error_sig["error_type"]
        change_type = fix_pattern["change_type"]

        lessons = {
            "SyntaxError": "Syntax errors often require fixing malformed code structure",
            "NameError": "Always define variables before using them",
            "AttributeError": "Check object types before accessing attributes",
            "TypeError": "Ensure type compatibility in operations",
            "IndentationError": "Python requires consistent indentation",
            "ImportError": "Verify module names and import paths",
        }

        base_lesson = lessons.get(error_type)

        if change_type == "addition":
            return f"{base_lesson or ''} - often fixed by adding missing code".strip()
        elif change_type == "deletion":
            return f"{base_lesson or ''} - often fixed by removing invalid code".strip()
        elif change_type == "modification":
            return f"{base_lesson or ''} - often fixed by modifying existing code".strip()

        return base_lesson


class Orienter:
    """
    Orient: Query context memory and find relevant patterns.

    Uses LocalContextTree for persistent learning across iterations.
    """

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.context_tree = LocalContextTree(project_root)
        self.extractor = PatternExtractor()

    def query_context(
        self,
        error_message: str,
        file_path: str,
        iteration: int = 0
    ) -> Dict[str, Any]:
        """
        Main orient method: query context for relevant information.

        Returns context to guide the decide phase, including:
        - similar_errors: Past errors that match the current one
        - file_history: History of changes to this file
        - lessons_learned: Accumulated wisdom from past iterations
        - error_signature: Structured error information
        """
        # Get relevant context from LocalContextTree
        context = self.context_tree.get_relevant_context(
            error_message=error_message,
            file_path=file_path
        )

        # Add structured error signature
        error_sig = self.extractor.extract_error_signature(error_message)
        context["error_signature"] = error_sig

        # Add pattern-based suggestions
        if context["similar_errors"]:
            context["suggestion"] = self._generate_suggestion(
                error_sig,
                context["similar_errors"]
            )

        return context

    def record_result(
        self,
        error: str,
        fix: str,
        file_path: str,
        success: bool,
        iteration: int
    ):
        """
        Record the result of an iteration for future learning.

        Updates patterns, lessons, and context tree.
        """
        # Record error-fix pattern
        self.context_tree.record_error_fix(
            error=error,
            fix=fix,
            file_path=file_path,
            success=success,
            iteration=iteration
        )

        # Extract and add lesson if successful
        if success:
            lesson = self.extractor.generate_lesson(error, fix, success, iteration)
            if lesson:
                self.context_tree.add_lesson(lesson)

    def create_iteration_record(
        self,
        iteration: int,
        observe: Dict,
        orient: Dict,
        decide: Dict,
        act: Dict,
        outcome: str
    ):
        """Create and store a complete iteration record."""
        from datetime import datetime

        record = IterationRecord(
            number=iteration,
            timestamp=datetime.now().isoformat(),
            observe=observe,
            orient=orient,
            decide=decide,
            act=act,
            outcome=outcome
        )
        self.context_tree.add_iteration(record)

    def get_statistics(self) -> Dict[str, Any]:
        """Get context tree statistics for monitoring."""
        return self.context_tree.get_statistics()

    def _generate_suggestion(
        self,
        error_sig: Dict,
        similar_errors: List[Dict]
    ) -> str:
        """Generate a suggestion based on similar past errors."""
        if not similar_errors:
            return ""

        # Get the most similar successful fix
        for pattern in similar_errors:
            if pattern.get("success", False):
                return f"Similar error was fixed by: {pattern.get('fix', 'N/A')[:100]}..."

        return "Similar errors seen before, but no successful fix on record."

    # Legacy methods for backward compatibility
    def find_similar_errors(self, error_message: str) -> List[dict]:
        """Find similar past errors (legacy)."""
        return self.context_tree.find_similar_errors(error_message)

    def get_lessons_learned(self) -> List[str]:
        """Get lessons learned (legacy)."""
        return self.context_tree.lessons

    def add_pattern(self, error: str, fix: str, success: bool):
        """Add pattern (legacy - use record_result instead)."""
        self.context_tree.record_error_fix(error, fix, "", success, 0)

    def _get_file_history(self, file_path: str) -> List[dict]:
        """Get file history (legacy)."""
        return self.context_tree.get_file_history(file_path)
