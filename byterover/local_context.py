"""
Local Context Tree for AutoDev.

Manages persistent memory across OODA iterations for learning.
"""
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict


@dataclass
class ContextNode:
    """A node in the context tree."""
    id: str
    type: str  # "error", "fix", "lesson", "code_snapshot"
    content: str
    metadata: Dict[str, Any]
    created_at: str
    parent_id: Optional[str] = None
    embedding: Optional[List[float]] = None


@dataclass
class IterationRecord:
    """Record of a complete OODA iteration."""
    number: int
    timestamp: str
    observe: Dict[str, Any]
    orient: Dict[str, Any]
    decide: Dict[str, Any]
    act: Dict[str, Any]
    outcome: str  # "success", "failed", "partial"


class LocalContextTree:
    """
    Persistent context tree for AutoDev.

    Stores:
    - Error patterns and their fixes
    - Code snapshots with success/failure
    - Lessons learned from iterations
    """

    def __init__(self, root_path: Path):
        self.root_path = root_path
        self.context_file = root_path / "logs" / "context_tree.json"
        self.patterns_file = root_path / "logs" / "patterns.json"
        self.lessons_file = root_path / "logs" / "lessons_learned.json"

        self.nodes: List[ContextNode] = []
        self.iterations: List[IterationRecord] = []
        self.patterns: List[Dict] = []
        self.lessons: List[str] = []

        self._load()

    def _load(self):
        """Load existing context from disk."""
        if self.context_file.exists():
            data = json.loads(self.context_file.read_text())
            self.nodes = [ContextNode(**n) for n in data.get("nodes", [])]
            self.iterations = [
                IterationRecord(**i) for i in data.get("iterations", [])
            ]

        if self.patterns_file.exists():
            data = json.loads(self.patterns_file.read_text())
            self.patterns = data.get("error_patterns", [])

        if self.lessons_file.exists():
            data = json.loads(self.lessons_file.read_text())
            self.lessons = data.get("lessons", [])

    def _save(self):
        """Save context to disk."""
        self.context_file.parent.mkdir(parents=True, exist_ok=True)

        # Save main context
        data = {
            "nodes": [asdict(n) for n in self.nodes],
            "iterations": [asdict(i) for i in self.iterations],
            "last_updated": datetime.now().isoformat()
        }
        self.context_file.write_text(json.dumps(data, indent=2))

        # Save patterns
        patterns_data = {
            "error_patterns": self.patterns,
            "last_updated": datetime.now().isoformat()
        }
        self.patterns_file.write_text(json.dumps(patterns_data, indent=2))

        # Save lessons
        lessons_data = {
            "lessons": self.lessons,
            "last_updated": datetime.now().isoformat()
        }
        self.lessons_file.write_text(json.dumps(lessons_data, indent=2))

    def add_node(self, node: ContextNode):
        """Add a node to the context tree."""
        self.nodes.append(node)
        self._save()

    def add_iteration(self, iteration: IterationRecord):
        """Add an iteration record."""
        self.iterations.append(iteration)
        self._save()

    def record_error_fix(
        self,
        error: str,
        fix: str,
        file_path: str,
        success: bool,
        iteration: int
    ):
        """Record an error-fix pattern."""
        pattern = {
            "id": self._hash_id(error + fix),
            "error": error,
            "error_type": self._classify_error(error),
            "fix": fix,
            "file": file_path,
            "success": success,
            "iteration": iteration,
            "timestamp": datetime.now().isoformat(),
            "occurrence_count": 1
        }

        # Check for similar existing patterns
        for existing in self.patterns:
            if existing["error"] == error:
                existing["occurrence_count"] += 1
                existing["last_seen"] = datetime.now().isoformat()
                self._save()
                return

        self.patterns.append(pattern)
        self._save()

    def add_lesson(self, lesson: str):
        """Add a lesson learned."""
        if lesson not in self.lessons:
            self.lessons.append(lesson)
            self._save()

    def find_similar_errors(
        self,
        error_message: str,
        threshold: float = 0.3
    ) -> List[Dict]:
        """
        Find similar past errors using keyword matching.

        Returns patterns sorted by similarity score.
        """
        error_lower = error_message.lower()
        error_words = set(error_lower.split())

        scored = []

        for pattern in self.patterns:
            pattern_lower = pattern["error"].lower()
            pattern_words = set(pattern_lower.split())

            # Jaccard similarity
            intersection = error_words & pattern_words
            union = error_words | pattern_words
            similarity = len(intersection) / len(union) if union else 0

            # Boost for exact substring matches
            if pattern_lower in error_lower or error_lower in pattern_lower:
                similarity += 0.3

            # Boost for same file
            # Note: file info would be passed in context
            if similarity > threshold:
                scored.append({**pattern, "similarity": similarity})

        # Sort by similarity (descending), then by occurrence count
        scored.sort(key=lambda p: (p["similarity"], p["occurrence_count"]), reverse=True)
        return scored

    def get_file_history(self, file_path: str) -> List[Dict]:
        """Get history of changes for a specific file."""
        history = []

        for iteration in self.iterations:
            for change in iteration.act.get("changes", []):
                if change.get("file") == file_path:
                    history.append({
                        "iteration": iteration.number,
                        "change": change,
                        "outcome": iteration.outcome,
                        "timestamp": iteration.timestamp
                    })

        # Sort by iteration number (ascending)
        history.sort(key=lambda h: h["iteration"])
        return history

    def get_relevant_context(
        self,
        error_message: str,
        file_path: str
    ) -> Dict[str, Any]:
        """
        Get all relevant context for a new error.

        Returns:
            Dict with similar_errors, file_history, and lessons_learned
        """
        return {
            "similar_errors": self.find_similar_errors(error_message),
            "file_history": self.get_file_history(file_path),
            "lessons_learned": self.lessons,
            "total_patterns": len(self.patterns),
            "total_iterations": len(self.iterations)
        }

    def _classify_error(self, error: str) -> str:
        """Classify error type for better matching."""
        error_lower = error.lower()

        if "syntax" in error_lower:
            return "syntax"
        elif "import" in error_lower or "module" in error_lower:
            return "import"
        elif "type" in error_lower and "error" in error_lower:
            return "type_error"
        elif "name" in error_lower and "not defined" in error_lower:
            return "name_error"
        elif "attribute" in error_lower:
            return "attribute_error"
        elif "indent" in error_lower:
            return "indentation"
        elif "test" in error_lower or "assert" in error_lower:
            return "test_failure"
        else:
            return "unknown"

    def _hash_id(self, content: str) -> str:
        """Generate stable ID from content."""
        return hashlib.md5(content.encode()).hexdigest()[:12]

    def get_statistics(self) -> Dict[str, Any]:
        """Get context tree statistics."""
        error_types = {}
        for pattern in self.patterns:
            etype = pattern.get("error_type", "unknown")
            error_types[etype] = error_types.get(etype, 0) + 1

        successful_patterns = sum(1 for p in self.patterns if p.get("success", False))

        return {
            "total_nodes": len(self.nodes),
            "total_iterations": len(self.iterations),
            "total_patterns": len(self.patterns),
            "successful_patterns": successful_patterns,
            "failed_patterns": len(self.patterns) - successful_patterns,
            "total_lessons": len(self.lessons),
            "error_types": error_types,
            "success_rate": (
                successful_patterns / len(self.patterns)
                if self.patterns else 0
            )
        }
