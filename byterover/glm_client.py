"""
GLM-4.5-Air API Client for Byterover

Handles communication with the GLM Coding Plan API.
"""

import os
import json
import requests
from typing import List, Dict, Optional


class GLMClient:
    """Client for GLM-4.5-Air API via Coding Plan endpoint."""

    CODING_ENDPOINT = "https://api.bigmodel.cn/api/paas/v4/chat/completions"
    DEFAULT_MODEL = "glm-4.7"  # Changed from glm-4.5-air (returns empty responses)

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the GLM client.

        Args:
            api_key: GLM Coding Plan API key. If None, reads from environment.
        """
        self.api_key = api_key or os.getenv("GLM_CODING_API_KEY") or os.getenv("ZHIPU_API_KEY")

        if not self.api_key:
            # Try config file
            config_path = os.path.expanduser("~/.claude/byterover/config.json")
            try:
                with open(config_path, "r") as f:
                    config = json.load(f)
                    self.api_key = config.get("glm_coding_api_key") or config.get("zhipu_api_key")
            except FileNotFoundError:
                pass

        if not self.api_key:
            raise ValueError(
                "GLM Coding Plan API key not found. "
                "Set GLM_CODING_API_KEY environment variable or "
                "create ~/.claude/byterover/config.json"
            )

        self.endpoint = self.CODING_ENDPOINT

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = DEFAULT_MODEL,
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ) -> Dict:
        """Send a chat completion request.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model name to use
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature

        Returns:
            Response dict with content and metadata
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        response = requests.post(
            self.endpoint,
            headers=headers,
            json=payload,
            timeout=60
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"GLM API error (HTTP {response.status_code}): {response.text}"
            )

        data = response.json()
        return {
            "content": data["choices"][0]["message"]["content"],
            "model": data.get("model", model),
            "usage": {
                "total_tokens": data["usage"]["total_tokens"],
                "prompt_tokens": data["usage"]["prompt_tokens"],
                "completion_tokens": data["usage"]["completion_tokens"],
            }
        }

    def analyze_query(self, query: str) -> Dict:
        """Analyze a query to determine context needs.

        Args:
            query: User's question or request

        Returns:
            Dict with analysis results
        """
        system_prompt = """You are a context analysis agent for a codebase.
Analyze the query and determine what context would be needed.
Respond in JSON format with:
{
  "needs_context": bool,
  "context_type": str (e.g., "code_pattern", "api_usage", "architecture"),
  "keywords": [str],
  "suggested_search_paths": [str]
}"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Analyze this query: {query}"}
        ]

        result = self.chat(messages, max_tokens=300, temperature=0.3)

        # Try to parse JSON from response
        import re
        json_match = re.search(r'\{.*\}', result["content"], re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        # Fallback if JSON parsing fails
        return {
            "needs_context": True,
            "context_type": "general",
            "keywords": [],
            "raw_analysis": result["content"]
        }

    def summarize_search_results(
        self,
        query: str,
        search_results: str,
        max_bullets: int = 5
    ) -> str:
        """Summarize search results for a query.

        Args:
            query: The original question/search
            search_results: Raw search results to summarize
            max_bullets: Maximum bullet points in summary

        Returns:
            Condensed summary string
        """
        system_prompt = f"""You are a context summarization agent.
Summarize search results concisely, extracting only the most relevant information.
Max {max_bullets} bullet points.
Focus on actionable information relevant to the query."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Query: {query}\n\nSearch Results:\n{search_results}"}
        ]

        result = self.chat(messages, max_tokens=500, temperature=0.5)
        return result["content"]

    def extract_patterns(self, code: str, context: str) -> str:
        """Extract code patterns from source code.

        Args:
            code: Source code to analyze
            context: What type of patterns to extract

        Returns:
            Extracted patterns documentation
        """
        system_prompt = """You are a code pattern extraction agent.
Analyze the given code and extract reusable patterns.
Focus on:
- Implementation patterns
- API usage conventions
- Best practices demonstrated
- Common pitfalls to avoid

Return structured documentation with examples."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context: {context}\n\nCode:\n{code}"}
        ]

        result = self.chat(messages, max_tokens=1500, temperature=0.5)
        return result["content"]


def create_client() -> GLMClient:
    """Factory function to create a GLM client.

    Reads API key from environment or config file.
    """
    return GLMClient()
