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
from pydantic import ValidationError

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
    select_small_models,
)

load_dotenv()

# Configurable benchmark model list
BENCHMARK_MODELS: List[str] = [
    "gpt-5-nano",
    "deepseek-coder:6.7b",
    "gemma3:1b",
    "gemma3:4b",
    "granite3.2-vision:2b",
    "llama2:7b",
    "meditron:7b",
    "moondream:1.8b",
    "qwen2.5-coder:7b",
    "qwen3:0.6b",
    "qwen3:4b",
]

# Maximum model size in billions of parameters (0.0 means no limit)
MAX_MODEL_SIZE_B: float = 4


def _select_benchmark_models() -> List[str]:
    """Select models from BENCHMARK_MODELS, filtered by installation and size limit.
    
    Always includes 'gpt-5-nano' (OpenAI baseline) unconditionally.
    For Ollama models: checks installation status and applies MAX_MODEL_SIZE_B filter.
    """
    available = {m.model for m in ollama_list().models}
    selected: List[str] = []
    
    # Always include OpenAI baseline
    selected.append("gpt-5-nano")
    
    # Filter Ollama models from BENCHMARK_MODELS
    ollama_candidates = [m for m in BENCHMARK_MODELS if m != "gpt-5-nano"]
    
    if MAX_MODEL_SIZE_B > 0.0:
        # Apply size limit and check installation
        ollama_candidates = select_small_models(ollama_candidates, max_b=MAX_MODEL_SIZE_B)
    
    # Only include models that are actually installed
    for model in ollama_candidates:
        if model in available:
            selected.append(model)
    
    if len(selected) == 1:  # Only gpt-5-nano
        pytest.skip("No Ollama models from BENCHMARK_MODELS are available.")
    
    return selected


def _metrics(parsed: ResumeProjectSummary) -> tuple[float, float, float]:
    mirage_rate, _, _ = mirage_metric(parsed, PROJECT_SNAPSHOT)
    grounding_rate, _, _ = entity_grounding_metric(parsed, PROJECT_SNAPSHOT)
    redundancy_rate, _, _ = redundancy_metric(parsed)
    return mirage_rate, grounding_rate, redundancy_rate


def _score(mirage: float, grounding: float, redundancy: float) -> float:
    # Higher is better: reward grounding, penalize mirage and redundancy.
    return ((1.0 - mirage) + grounding + (1.0 - redundancy)) / 3.0


def _bar(value: float, width: int = 12) -> str:
    clamped = max(0.0, min(1.0, value))
    filled = int(round(clamped * width))
    return f"{'#' * filled}{'-' * (width - filled)}"


def _render_table(
    prompt_name: str, rows: List[tuple[str, float, float, float, float]]
) -> str:
    headers = [
        "Model",
        "Secs",
        "Mirage (lower is better)",
        "Grounding (higher is better)",
        "Redundancy (lower is better)",
    ]
    model_width = max(len(headers[0]), max(len(row[0]) for row in rows))
    secs_width = len(headers[1])
    lines = [f"Prompt: {prompt_name}"]
    bar_width = 12
    metric_width = max(
        max(len(header) for header in headers[2:]), len(f"0.00 {'#' * bar_width}")
    )
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
                    f"{mirage:.2f} {_bar(mirage, bar_width)}",
                    f"{grounding:.2f} {_bar(grounding, bar_width)}",
                    f"{redundancy:.2f} {_bar(redundancy, bar_width)}",
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
    candidates: List[tuple[str, float, float, float, float, str]] = [
        (
            "gpt-5-nano",
            openai_mirage,
            openai_grounding,
            openai_redundancy,
            _score(openai_mirage, openai_grounding, openai_redundancy),
            baseline_content.strip(),
        )
    ]
    invalid_models: List[str] = []

    for model in _select_benchmark_models():
        if model == "gpt-5-nano":
            continue  # Already processed as baseline
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

        try:
            parsed = ResumeProjectSummary.model_validate_json(message_content)
        except ValidationError:
            invalid_models.append(model)
            continue

        mirage_rate, grounding_rate, redundancy_rate = _metrics(parsed)
        rows.append((model, elapsed, mirage_rate, grounding_rate, redundancy_rate))
        candidates.append(
            (
                model,
                mirage_rate,
                grounding_rate,
                redundancy_rate,
                _score(mirage_rate, grounding_rate, redundancy_rate),
                message_content.strip(),
            )
        )

    if len(rows) == 1:
        pytest.fail("No Ollama models returned valid JSON for this prompt.")

    print(_render_table(prompt_name, rows))

    top_candidates = sorted(candidates, key=lambda item: item[4], reverse=True)[:3]
    print("Top 3 responses:")
    for rank, (model, mirage, grounding, redundancy, score, content) in enumerate(
        top_candidates, start=1
    ):
        print(
            "\n".join(
                [
                    f"#{rank} {model}",
                    f"Score: {score:.3f}",
                    f"Mirage: {mirage:.2f}",
                    f"Grounding: {grounding:.2f}",
                    f"Redundancy: {redundancy:.2f}",
                    "Response:",
                    content,
                    "---",
                ]
            )
        )

    if invalid_models:
        print(f"Invalid JSON outputs: {', '.join(invalid_models)}")
