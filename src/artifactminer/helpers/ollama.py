"""Utilities for interacting with a local Ollama LLM."""

from ollama import chat
from pydantic import BaseModel

__all__ = ["get_ollama_response"]

DEFAULT_MODEL = "llama3"  # or mistral, gemma, etc.


class OllamaTextResponse(BaseModel):
    content: str


def get_ollama_response(prompt: str, model: str = DEFAULT_MODEL) -> str:
    try:
        response = chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            format=OllamaTextResponse.model_json_schema(),
        )
        message_content = response.message.content
        if message_content is None:
            raise ValueError("Ollama response content was empty.")
        parsed = OllamaTextResponse.model_validate_json(message_content)
        return parsed.content.strip()
    except Exception as exc:
        return f"[Ollama error] {exc}"
