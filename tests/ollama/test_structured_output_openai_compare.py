"""Compare Ollama structured output against an OpenAI baseline."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import List

import pytest
from dotenv import load_dotenv
from ollama import chat, list as ollama_list

MODULE_DIR = Path(__file__).resolve().parent
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from artifactminer.helpers.openai import get_gpt5_nano_response_sync
from structured_output_common import (
    OLLAMA_MODELS,
    PROJECT_SNAPSHOT,
    ResumeProjectSummary,
    entity_grounding_metric,
    mirage_metric,
    prompt_variants,
    redundancy_metric,
)

load_dotenv()


def _available_models() -> List[str]:
    available = {m.model for m in ollama_list().models}
    selected = [m for m in OLLAMA_MODELS if m in available]
    if not selected:
        pytest.skip("No requested Ollama models are available.")
    return selected


def _metrics(parsed: ResumeProjectSummary) -> tuple[float, float, float]:
    mirage_rate, _, _ = mirage_metric(parsed, PROJECT_SNAPSHOT)
    grounding_rate, _, _ = entity_grounding_metric(parsed, PROJECT_SNAPSHOT)
    redundancy_rate, _, _ = redundancy_metric(parsed)
    return mirage_rate, grounding_rate, redundancy_rate


def _bar(value: float, width: int = 12) -> str:
    clamped = max(0.0, min(1.0, value))
    filled = int(round(clamped * width))
    return f"{'#' * filled}{'-' * (width - filled)}"


def _render_table(
    prompt_name: str, rows: List[tuple[str, float, float, float, float]]
) -> str:
    headers = ["Model", "Secs", "Mirage", "Grounding", "Redundancy"]
    model_width = max(len(headers[0]), max(len(row[0]) for row in rows))
    secs_width = len(headers[1])
    lines = [f"Prompt: {prompt_name}"]
    metric_width = 18
    lines.append(
        " ".join(
            [
                f"{headers[0]:<{model_width}}",
                f"{headers[1]:>{secs_width}}",
                f"{headers[2]:<{metric_width}}",
                f"{headers[3]:<{metric_width}}",
                f"{headers[4]:<{metric_width}}",
            ]
        )
    )
    for model, seconds, mirage, grounding, redundancy in rows:
        lines.append(
            " ".join(
                [
                    f"{model:<{model_width}}",
                    f"{seconds:>{secs_width}.2f}",
                    f"{mirage:.2f} {_bar(mirage)}",
                    f"{grounding:.2f} {_bar(grounding)}",
                    f"{redundancy:.2f} {_bar(redundancy)}",
                ]
            )
        )
    return "\n".join(lines)


@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY")
    or os.getenv("OPENAI_API_KEY") == "your_openai_api_key_here",
    reason="OPENAI_API_KEY not set in environment or using placeholder value",
)
@pytest.mark.parametrize("prompt_name,prompt", prompt_variants())
def test_structured_output_openai_compare(prompt_name: str, prompt: str) -> None:
    baseline_start = time.monotonic()
    baseline_content = get_gpt5_nano_response_sync(prompt)
    baseline_seconds = time.monotonic() - baseline_start
    assert baseline_content, "OpenAI response content was empty."

    baseline_parsed = ResumeProjectSummary.model_validate_json(baseline_content)
    assert baseline_parsed.project_name.strip()
    assert baseline_parsed.one_liner.strip()
    assert baseline_parsed.highlights
    assert baseline_parsed.skills

    openai_mirage, openai_grounding, openai_redundancy = _metrics(baseline_parsed)
    rows: List[tuple[str, float, float, float, float]] = [
        ("gpt-5-nano", baseline_seconds, openai_mirage, openai_grounding, openai_redundancy)
    ]

    for model in _available_models():
        start_time = time.monotonic()
        response = chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            format=ResumeProjectSummary.model_json_schema(),
            options={"temperature": 0},
        )
        elapsed = time.monotonic() - start_time

        message_content = response.message.content
        assert message_content, "Ollama response content was empty."

        parsed = ResumeProjectSummary.model_validate_json(message_content)
        mirage_rate, grounding_rate, redundancy_rate = _metrics(parsed)
        rows.append((model, elapsed, mirage_rate, grounding_rate, redundancy_rate))

    print(_render_table(prompt_name, rows))
