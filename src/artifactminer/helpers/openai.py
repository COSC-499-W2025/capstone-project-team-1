"""Utilities for interacting with the OpenAI Responses API."""

from typing import List

from dotenv import load_dotenv
from openai import AsyncOpenAI, OpenAI

load_dotenv()

__all__ = ["get_gpt5_nano_response", "get_gpt5_nano_response_sync"]

# Create a single shared client instance for all async requests
# This avoids the overhead of creating a new client for each query
_async_client = AsyncOpenAI()

# Create a single shared client instance for all sync requests
_sync_client = OpenAI()


async def get_gpt5_nano_response(prompt: str) -> str:
    """Call the OpenAI Responses API with the gpt-5-nano model and return plain text (async).

    Args:
        prompt: The string to send to the model.

    Returns:
        The model output as a plain string. If no textual content is present, an
        empty string is returned.
    """

    # Use the shared async client instance
    response = await _async_client.responses.create(
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


def get_gpt5_nano_response_sync(prompt: str) -> str:
    """Synchronous version - Call the OpenAI Responses API with the gpt-5-nano model and return plain text.

    Args:
        prompt: The string to send to the model.

    Returns:
        The model output as a plain string. If no textual content is present, an
        empty string is returned.
    """

    # Use the shared sync client instance
    response = _sync_client.responses.create(
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
