"""
Anthropic Claude client for AutoDev.

Uses Claude via Anthropic's API for high-quality code generation.
"""

import os
import requests
from typing import List, Dict, Optional


class ClaudeClient:
    """Client for Anthropic Claude API."""

    DEFAULT_ENDPOINT = "https://api.anthropic.com/v1/messages"
    DEFAULT_MODEL = "claude-3-5-sonnet-20241022"

    def __init__(
        self,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        model: Optional[str] = None
    ):
        """Initialize the Claude client.

        Args:
            api_key: Anthropic API key. If None, reads from ANTHROPIC_API_KEY env var.
            endpoint: API endpoint.
            model: Default model to use.
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Anthropic API key not found. Set ANTHROPIC_API_KEY environment variable."
            )

        self.endpoint = endpoint or self.DEFAULT_ENDPOINT
        self.model = model or os.getenv("ANTHROPIC_MODEL", self.DEFAULT_MODEL)

    def call(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.3
    ) -> str:
        """Generate a patch using Claude.

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
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }

        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }

        response = requests.post(
            self.endpoint,
            headers=headers,
            json=payload,
            timeout=60
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"Claude API error (HTTP {response.status_code}): {response.text}"
            )

        data = response.json()
        return data["content"][0]["text"]


def create_client():
    """Create a Claude client for AutoDev."""
    return ClaudeClient()
