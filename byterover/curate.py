"""
Curate Command for Byterover

Implements /curate - populate Context Tree from codebase.
"""

import os
import sys
from pathlib import Path
from typing import Optional, List

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from glm_client import GLMClient
from context_tree import ContextTree


def curate(
    topic: str,
    search_paths: Optional[List[str]] = None,
    category: str = "patterns",
    context_tree: Optional[ContextTree] = None,
    glm_client: Optional[GLMClient] = None
) -> dict:
    """Curate knowledge from the codebase into the Context Tree.

    Args:
        topic: Description of what to curate
        search_paths: List of paths to search (default: common code locations)
        category: Category to store under (patterns, architecture, apis, etc.)
        context_tree: ContextTree instance (created if None)
        glm_client: GLMClient instance (created if None)

    Returns:
        Dict with results including created entries
    """
    # Initialize clients
    if glm_client is None:
        glm_client = GLMClient()
    if context_tree is None:
        context_tree = ContextTree()

    print(f"\n[Curating] {topic}")
    print(f"   Category: {category}")

    # Default search paths for a JUCE plugin project
    if search_paths is None:
        search_paths = [
            "plugins",
            "src",
            "Source",
            "include",
            ".claude",
        ]
    else:
        # Use provided paths directly
        relevant_files = [p for p in search_paths if Path(p).exists()]
        print(f"   Using provided paths: {len(relevant_files)} files")

        # Skip keyword search if paths explicitly provided
        if not relevant_files:
            # Fall back to keyword search in default paths
            relevant_files = _find_relevant_files(topic, [
                "plugins", "src", "Source", "include", ".claude"
            ])

    # If no paths provided, do keyword search
    if search_paths is None or not relevant_files:
        relevant_files = _find_relevant_files(topic, search_paths if search_paths else [
            "plugins", "src", "Source", "include", ".claude"
        ])
    print(f"   Found {len(relevant_files)} relevant files")

    if not relevant_files:
        return {
            "success": False,
            "message": "No relevant files found for curation",
            "topic": topic,
            "category": category,
        }

    # Extract patterns from relevant files
    entries_created = []

    for filepath in relevant_files[:3]:  # Limit to top 3 files for now
        print(f"   Processing: {filepath}")

        try:
            content = _read_file(filepath)

            # Use GLM-4.5-Air to extract patterns
            extracted = glm_client.extract_patterns(content, topic)

            # Add to Context Tree
            title = f"{topic} - {Path(filepath).stem}"
            entry_path = context_tree.add_knowledge(
                category=category,
                title=title,
                content=extracted,
                tags=[topic, category, Path(filepath).stem],
                metadata={"source_file": str(filepath)}
            )

            entries_created.append({
                "file": str(filepath),
                "entry_path": str(entry_path),
                "title": title,
            })

            print(f"     --> Created: {entry_path.name}")

        except Exception as e:
            print(f"     [Error] {e}")
            continue

    return {
        "success": True,
        "topic": topic,
        "category": category,
        "entries_created": entries_created,
        "message": f"Created {len(entries_created)} knowledge entries",
    }


def _find_relevant_files(topic: str, search_paths: List[str]) -> List[str]:
    """Find relevant files based on topic keywords.

    Simple keyword matching - could be enhanced with GLM-4.5-Air analysis.
    """
    # Extract keywords from topic
    keywords = topic.lower().split()

    relevant_files = []

    for search_path in search_paths:
        path = Path(search_path)
        if not path.exists():
            continue

        # Find source files
        for extension in [".cpp", ".h", ".py", ".md", ".js", ".ts"]:
            for filepath in path.rglob(f"*{extension}"):
                # Simple keyword check in filename
                if any(keyword in filepath.name.lower() for keyword in keywords):
                    relevant_files.append(str(filepath))

    return relevant_files


def _read_file(filepath: str, max_lines: int = 200) -> str:
    """Read file content, limiting lines for large files.

    Args:
        filepath: Path to file
        max_lines: Maximum lines to read

    Returns:
        File content as string
    """
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            lines = []
            for i, line in enumerate(f):
                if i >= max_lines:
                    break
                lines.append(line)
            return "".join(lines)
    except Exception as e:
        return f"# Error reading file: {e}"


def main():
    """CLI entry point for curate command."""
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Curate knowledge into Byterover Context Tree")
    parser.add_argument("topic", help="What to curate (e.g., 'JUCE convolution reverb')")
    parser.add_argument("--category", default="patterns",
                       choices=["patterns", "architecture", "apis", "decisions", "troubleshooting"],
                       help="Category to store under")
    parser.add_argument("--paths", nargs="+", help="Paths to search (default: common locations)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    try:
        result = curate(
            topic=args.topic,
            search_paths=args.paths,
            category=args.category,
        )

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print("\n" + "="*60)
            print("CURATION RESULTS")
            print("="*60)
            print(f"Topic: {result['topic']}")
            print(f"Category: {result['category']}")
            print(f"\n{result['message']}")

            if result.get("entries_created"):
                print("\nEntries created:")
                for entry in result["entries_created"]:
                    print(f"  • {entry['title']}")
                    print(f"    Source: {entry['file']}")
            print("="*60)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
