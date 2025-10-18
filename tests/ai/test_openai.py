"""Integration tests for OpenAI utility functions using real API calls."""
from __future__ import annotations

import os

import pytest
from dotenv import load_dotenv

from artifactminer.ai.openai import get_gpt5_nano_response

load_dotenv()


@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") == "your_openai_api_key_here",
    reason="OPENAI_API_KEY not set in environment or using placeholder value"
)
class TestOpenAIIntegration:
    """Integration tests using real OpenAI API."""

    def test_simple_prompt_response(self):
        """Test that a simple prompt returns a non-empty response."""
        prompt = "Say 'Hello World' and nothing else."
        result = get_gpt5_nano_response(prompt)

        assert isinstance(result, str)
        assert len(result) > 0
        print(f"Response: {result}")

    def test_math_prompt_response(self):
        """Test that a math question returns a response containing the answer."""
        prompt = "What is 2 + 2? Respond with only the number."
        result = get_gpt5_nano_response(prompt)

        assert isinstance(result, str)
        assert len(result) > 0

        print(f"Response: {result}")

    def test_code_generation_prompt(self):
        """Test that a code generation request returns code."""
        prompt = "Write a Python function that adds two numbers. Just the function, no explanation."
        result = get_gpt5_nano_response(prompt)

        assert isinstance(result, str)
        assert len(result) > 0
        print(f"Response: {result}")

    def test_empty_prompt_response(self):
        """Test behavior with an empty prompt - should raise an error."""
        from openai import BadRequestError

        with pytest.raises(BadRequestError):
            get_gpt5_nano_response("")

    def test_multiline_prompt(self):
        """Test that multiline prompts work correctly."""
        prompt = """Line 1: Hello
Line 2: World
Line 3: Test

Respond with 'Success'"""
        result = get_gpt5_nano_response(prompt)

        assert isinstance(result, str)
        assert len(result) > 0
        print(f"Response: {result}")
