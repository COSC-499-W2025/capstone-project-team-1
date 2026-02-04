from __future__ import annotations

from ollama import chat

DEFAULT_MODEL = "qwen3:4b"


def get_ollama_response(prompt: str, model: str = DEFAULT_MODEL) -> str:
    response = chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0.3},
    )
    return response.message.content
