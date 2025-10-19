"""Utilities for interacting with the OpenAI Responses API."""

from dotenv import load_dotenv
from openai import OpenAI
from typing import List

load_dotenv()

__all__ = ["get_gpt5_nano_response"]


def get_gpt5_nano_response(prompt: str) -> str:
    """Call the OpenAI Responses API with the gpt-5-nano model and return plain text.

    Args:
        prompt: The string to send to the model.

    Returns:
        The model output as a plain string. If no textual content is present, an
        empty string is returned.
    """

    response = OpenAI().responses.create(
        model="gpt-5-nano",
        input=prompt
    )

    if getattr(response, "output_text", None):
        return response.output_text

    text_parts: List[str] = []
    for item in getattr(response, "output", []) or []:
        for content in getattr(item, "content", []) or []:
            text = getattr(content, "text", None)
            if text and getattr(text, "value", None):
                text_parts.append(text.value)

    return "".join(text_parts)
