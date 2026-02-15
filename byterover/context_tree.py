"""
Context Tree Management for Byterover

Handles storage and retrieval of curated knowledge.
"""

import os
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional


class ContextTree:
    """Manages the Byterover Context Tree."""

    def __init__(self, base_path: Optional[Path] = None):
        """Initialize the Context Tree.

        Args:
            base_path: Base path for Context Tree. Defaults to .claude/byterover/
        """
        if base_path is None:
            # Find .claude directory
            cwd = Path.cwd()
            while cwd != cwd.parent:
                claude_dir = cwd / ".claude"
                if claude_dir.exists():
                    base_path = claude_dir / "byterover"
                    break
                cwd = cwd.parent
            else:
                # Fallback to current directory
                base_path = Path.cwd() / ".claude" / "byterover"

        self.base_path = Path(base_path)
        self.knowledge_path = self.base_path / "knowledge"
        self._ensure_structure()

    def _ensure_structure(self):
        """Create directory structure if it doesn't exist."""
        directories = [
            self.knowledge_path / "architecture",
            self.knowledge_path / "patterns",
            self.knowledge_path / "decisions",
            self.knowledge_path / "apis",
            self.knowledge_path / "troubleshooting",
            self.base_path / "config",
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    def add_knowledge(
        self,
        category: str,
        title: str,
        content: str,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict] = None
    ) -> Path:
        """Add knowledge to the Context Tree.

        Args:
            category: One of: architecture, patterns, decisions, apis, troubleshooting
            title: Title for the knowledge entry
            content: Main content (markdown)
            tags: Optional list of tags
            metadata: Optional metadata dict

        Returns:
            Path to created file

        Raises:
            ValueError: If category is invalid
        """
        valid_categories = ["architecture", "patterns", "decisions", "apis", "troubleshooting"]
        if category not in valid_categories:
            raise ValueError(f"Invalid category. Must be one of: {valid_categories}")

        # Create safe filename from title
        safe_title = title.lower().replace(" ", "-").replace("/", "-")[:50]
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"{timestamp}-{safe_title}.md"

        filepath = self.knowledge_path / category / filename

        # Build frontmatter
        frontmatter = {
            "title": title,
            "category": category,
            "created": datetime.now().isoformat(),
            "tags": tags or [],
        }
        if metadata:
            frontmatter.update(metadata)

        # Write file with YAML frontmatter
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("---\n")
            f.write(json.dumps(frontmatter, indent=2, ensure_ascii=False))
            f.write("\n---\n\n")
            f.write(content)

        return filepath

    def search(
        self,
        query: str,
        categories: Optional[List[str]] = None,
        tags: Optional[List[str]] = None
    ) -> List[Dict]:
        """Search the Context Tree.

        Args:
            query: Search query
            categories: Filter by categories (None = all)
            tags: Filter by tags (None = no tag filter)

        Returns:
            List of matching entries with metadata and content
        """
        results = []

        # Determine which directories to search
        if categories:
            search_dirs = [self.knowledge_path / cat for cat in categories]
        else:
            # Search all category subdirectories
            search_dirs = [
                self.knowledge_path / cat
                for cat in ["architecture", "patterns", "decisions", "apis", "troubleshooting"]
            ]

        for directory in search_dirs:
            if not directory.exists():
                continue

            for filepath in directory.glob("*.md"):
                try:
                    entry = self._parse_entry(filepath)

                    # Apply filters
                    if tags and not any(tag in entry.get("tags", []) for tag in tags):
                        continue

                    # Simple text search (could be enhanced with proper search)
                    content_lower = entry.get("content", "").lower()
                    query_lower = query.lower()
                    title_lower = entry.get("title", "").lower()

                    if query_lower in content_lower or query_lower in title_lower:
                        results.append(entry)

                except Exception:
                    # Skip files that can't be parsed
                    continue

        return results

    def _parse_entry(self, filepath: Path) -> Dict:
        """Parse a knowledge entry file.

        Returns dict with metadata and content.
        """
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # Parse YAML frontmatter
        metadata = {}
        body_content = content

        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                try:
                    metadata = json.loads(parts[1])
                    body_content = parts[2].strip()
                except json.JSONDecodeError:
                    body_content = content

        return {
            "path": str(filepath),
            "title": metadata.get("title", filepath.stem),
            "category": metadata.get("category"),
            "created": metadata.get("created"),
            "tags": metadata.get("tags", []),
            "metadata": metadata,
            "content": body_content,
        }

    def get_all_categories(self) -> List[str]:
        """Get list of all categories with entries."""
        categories = []
        for category in ["architecture", "patterns", "decisions", "apis", "troubleshooting"]:
            cat_path = self.knowledge_path / category
            if cat_path.exists() and list(cat_path.glob("*.md")):
                categories.append(category)
        return categories

    def get_stats(self) -> Dict:
        """Get statistics about the Context Tree."""
        stats = {
            "total_entries": 0,
            "by_category": {},
        }

        for category in ["architecture", "patterns", "decisions", "apis", "troubleshooting"]:
            cat_path = self.knowledge_path / category
            if cat_path.exists():
                entries = list(cat_path.glob("*.md"))
                count = len(entries)
                stats["by_category"][category] = count
                stats["total_entries"] += count

        return stats


def create_context_tree() -> ContextTree:
    """Factory function to create a Context Tree."""
    return ContextTree()
