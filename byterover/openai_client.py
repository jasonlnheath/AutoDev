"""
OpenAI-compatible LLM client for AutoDev.

Supports OpenAI GPT-4, o1, Claude via OpenAI, or any OpenAI-compatible API.
"""

import os
import requests
from typing import List, Dict, Optional


class OpenAIClient:
    """Client for OpenAI-compatible APIs."""

    DEFAULT_ENDPOINT = "https://api.openai.com/v1/chat/completions"
    DEFAULT_MODEL = "gpt-4o-mini"  # Cost-effective for code patches

    def __init__(
        self,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        model: Optional[str] = None
    ):
        """Initialize the OpenAI client.

        Args:
            api_key: OpenAI API key. If None, reads from OPENAI_API_KEY env var.
            endpoint: API endpoint. Can use custom OpenAI-compatible services.
            model: Default model to use.
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenAI API key not found. Set OPENAI_API_KEY environment variable."
            )

        self.endpoint = endpoint or os.getenv("OPENAI_ENDPOINT", self.DEFAULT_ENDPOINT)
        self.model = model or os.getenv("OPENAI_MODEL", self.DEFAULT_MODEL)

    def call(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.3
    ) -> str:
        """Generate a patch using OpenAI.

        Args:
            prompt: The prompt to send
            model: Model override
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature

        Returns:
            Generated text response
        """
        model = model or self.model

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert code repair agent. Generate minimal patches in unified diff format."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
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
                f"OpenAI API error (HTTP {response.status_code}): {response.text}"
            )

        data = response.json()
        return data["choices"][0]["message"]["content"]


# Factory function for AutoDev compatibility
def create_client():
    """Create an OpenAI client for AutoDev."""
    return OpenAIClient()
