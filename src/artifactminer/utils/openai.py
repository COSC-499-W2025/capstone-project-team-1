"""Utilities for interacting with the OpenAI Responses API."""
from __future__ import annotations

from openai import OpenAI

__all__ = ["get_gpt5_mini_response"]


def get_gpt5_mini_response(prompt: str) -> str:
    """Call the OpenAI Responses API with the gpt5-mini model and return plain text.

    Args:
        prompt: The string to send to the model.

    Returns:
        The model output as a plain string. If no textual content is present, an
        empty string is returned.
    """

    response = OpenAI().responses.create(
        model="gpt5-mini", 
        input=prompt
    )

    if getattr(response, "output_text", None):
        return response.output_text

    text_parts: list[str] = []
    for item in getattr(response, "output", []) or []:
        for content in getattr(item, "content", []) or []:
            text = getattr(content, "text", None)
            if text and getattr(text, "value", None):
                text_parts.append(text.value)

    return "".join(text_parts)
