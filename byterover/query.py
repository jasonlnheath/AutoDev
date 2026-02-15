"""
Query Command for Byterover

Implements /query - search Context Tree and codebase for relevant information.
"""

import os
import sys
from pathlib import Path
from typing import Optional, List

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from glm_client import GLMClient
from context_tree import ContextTree


def query(
    query_text: str,
    include_web: bool = False,
    context_tree: Optional[ContextTree] = None,
    glm_client: Optional[GLMClient] = None
) -> str:
    """Execute a query against Context Tree and codebase.

    Args:
        query_text: The user's question or search query
        include_web: Whether to include web search results
        context_tree: ContextTree instance (created if None)
        glm_client: GLMClient instance (created if None)

    Returns:
        Summarized, relevant context
    """
    # Initialize clients
    if glm_client is None:
        glm_client = GLMClient()
    if context_tree is None:
        context_tree = ContextTree()

    print(f"\n[Analyzing] {query_text}")

    # Step 1: Analyze the query
    analysis = glm_client.analyze_query(query_text)
    print(f"   Context type: {analysis.get('context_type', 'general')}")
    print(f"   Keywords: {analysis.get('keywords', [])}")

    # Step 2: Search Context Tree
    context_results = context_tree.search(query_text)
    print(f"   Found {len(context_results)} entries in Context Tree")

    # Step 3: Gather relevant context
    context_parts = []

    if context_results:
        context_parts.append("## Context Tree Results\n")
        for entry in context_results[:5]:  # Top 5 results
            context_parts.append(f"### {entry['title']}")
            context_parts.append(f"Category: {entry['category']}")
            context_parts.append(entry['content'][:500])  # First 500 chars
            context_parts.append("---")

    # Step 4: If no context found, mention this
    if not context_results:
        context_parts.append("## Context Tree Search")
        context_parts.append("No matching entries found in Context Tree.")
        context_parts.append("Consider using /curate to populate relevant knowledge.")

    # Combine context for summarization
    combined_context = "\n\n".join(context_parts)

    # Step 5: Summarize with GLM-4.5-Air
    print("   Summarizing findings...")
    summary = glm_client.summarize_search_results(query_text, combined_context)

    return summary


def query_with_web(
    query_text: str,
    context_tree: Optional[ContextTree] = None,
    glm_client: Optional[GLMClient] = None
) -> str:
    """Execute a query including web search results.

    Args:
        query_text: The user's question or search query
        context_tree: ContextTree instance (created if None)
        glm_client: GLMClient instance (created if None)

    Returns:
        Summarized context from local + web sources
    """
    # First get local results
    local_summary = query(query_text, include_web=False, context_tree=context_tree, glm_client=glm_client)

    # For now, return local summary with note about web search
    # Web search integration will use the existing websearch skill
    return f"{local_summary}\n\n**Note:** Web search integration pending - use /websearch skill separately."


def main():
    """CLI entry point for query command."""
    import argparse

    parser = argparse.ArgumentParser(description="Query Byterover Context Tree")
    parser.add_argument("query", help="Your question or search query")
    parser.add_argument("--web", action="store_true", help="Include web search results")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    try:
        if args.web:
            result = query_with_web(args.query)
        else:
            result = query(args.query)

        if args.json:
            import json
            print(json.dumps({"result": result}, indent=2))
        else:
            print("\n" + "="*60)
            print("QUERY RESULTS")
            print("="*60)
            print(result)
            print("="*60)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
