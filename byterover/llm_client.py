"""
Universal LLM client for AutoDev.

Supports multiple backends: OpenAI, Anthropic, GLM, or any OpenAI-compatible API.
Configure via environment variables.
"""

import os
import sys
from pathlib import Path
from typing import Optional


def create_llm_client():
    """
    Factory function to create an LLM client based on environment configuration.

    Environment variables:
    - LLM_PROVIDER: "openai", "anthropic", "glm", or "custom"
    - OPENAI_API_KEY: For OpenAI-compatible APIs
    - ANTHROPIC_API_KEY: For Claude
    - GLM_CODING_API_KEY or ZHIPU_API_KEY: For GLM
    - OPENAI_ENDPOINT: Custom endpoint (for OpenAI-compatible services)
    - OPENAI_MODEL: Model name override
    """
    provider = os.getenv("LLM_PROVIDER", "glm").lower()

    # Get the byterover directory
    byterover_dir = Path(__file__).parent

    if provider == "anthropic":
        sys.path.insert(0, str(byterover_dir))
        from claude_client import ClaudeClient
        return ClaudeClient()
    elif provider == "glm":
        sys.path.insert(0, str(byterover_dir))
        from glm_client import GLMClient as _GLMClientClass
        return _GLMWrapper(_GLMClientClass())
    elif provider in ("openai", "custom"):
        sys.path.insert(0, str(byterover_dir))
        from openai_client import OpenAIClient
        return OpenAIClient()
    else:
        raise ValueError(
            f"Unknown LLM provider: {provider}. "
            "Supported: openai, anthropic, glm"
        )


class _GLMWrapper:
    """Wrapper to make GLMClient compatible with the universal interface."""

    def __init__(self, glm_client):
        self._client = glm_client

    def call(self, prompt: str, model: Optional[str] = None, max_tokens: int = 2000, temperature: float = 0.3) -> str:
        """Call GLM with the universal interface."""
        # GLM uses messages format
        messages = [
            {"role": "system", "content": "You are an expert code repair agent. Generate minimal patches in unified diff format."},
            {"role": "user", "content": prompt}
        ]

        result = self._client.chat(
            messages=messages,
            model=model or "glm-4.5-air",
            max_tokens=max_tokens,
            temperature=temperature
        )
        return result["content"]


class UniversalLLMClient:
    """
    Wrapper that provides a consistent interface for all LLM providers.

    Usage:
        client = UniversalLLMClient()
        response = client.call("Generate a patch for...")
    """

    def __init__(self, provider: Optional[str] = None):
        """Initialize with specific provider or use environment variable."""
        if provider:
            os.environ["LLM_PROVIDER"] = provider
        self._client = create_llm_client()

    def call(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.3
    ) -> str:
        """Generate text using the configured LLM."""
        return self._client.call(
            prompt=prompt,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature
        )


# For backward compatibility with existing code
def GLMClient():
    """Factory that returns the configured client (naming kept for compatibility)."""
    return create_llm_client()
