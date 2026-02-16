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
    # LLAMA
    "llama3.2:1b",
    "llama3.2:3b",
    "llama3.1:8b",
    # GEMMA
    "gemma3:4b",
    "gemma3:12b",
    "gemma2:2b",
    "gemma2:9b",
    "gemma:7b",
    # QWEN
    "qwen2.5:0.5b",
    "qwen2.5:1.5b",
    "qwen2.5:3b",
    "qwen2.5:7b",
    "qwen2.5:14b",
    "qwen3:4b",
    "qwen3:8b",
    "qwen3:14b",
    # DEEPSEEK
    "deepseek-r1:1.5b",
    "deepseek-r1:7b",
    "deepseek-r1:8b",
    "deepseek-r1:14b",
    # PHI
    "phi3:3.8b",
    "phi3:14b",
    "phi3.5:3.8b",
    "phi4:14b",
    "phi4-mini:3.8b",
    "phi4-mini-reasoning:3.8b",
    # MISTRAL
    "mistral:7b",
    "mistral-nemo:12b",
    "mixtral:8x7b",
    # IBM GRANITE
    "granite3-dense:2b",
    "granite3-dense:8b",
    "granite3.3:2b",
    "granite3.3:8b",
    "granite4:3b",
    # CODE MODELS
    "deepseek-coder:1.3b",
    "deepseek-coder:6.7b",
    "starcoder2:3b",
    "starcoder2:7b",
    "codegemma:2b",
    "codegemma:7b",
    "stable-code:3b",
    "codellama:7b",
    # SMALL + CHAT MODELS
    "tinyllama:1.1b",
    "smollm2:1.7b",
    "falcon3:3b",
    "falcon3:7b",
    "olmo2:7b",
    "openchat:7b",
    "neural-chat:7b",
    "starling-lm:7b",
    "dolphin-mistral:7b",
    "zephyr:7b",
    # COHERE
    "command-r7b",
]


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


def _progress_line(completed: int, total: int, elapsed: float) -> str:
    if total <= 0:
        return "Progress: 0/0"
    ratio = completed / total
    bar = _bar(ratio, 24)
    eta_seconds = (elapsed / completed * (total - completed)) if completed else 0.0
    return (
        f"Progress: {completed}/{total} [{bar}] "
        f"elapsed {elapsed:.1f}s, ETA {eta_seconds:.1f}s"
    )


def _print_progress(completed: int, total: int, elapsed: float) -> None:
    print(_progress_line(completed, total, elapsed), flush=True)


def _render_table(
    prompt_name: str,
    rows: List[tuple[str, float, float, float, float]],
    baseline_seconds: float,
) -> str:
    headers = [
        "Model",
        "Secs",
        "Δ vs ChatGPT (s)",
        "Mirage (lower is better)",
        "Grounding (higher is better)",
        "Redundancy (lower is better)",
    ]
    model_width = max(len(headers[0]), max(len(row[0]) for row in rows))
    secs_width = max(len(headers[1]), len(f"{max(row[1] for row in rows):.2f}"))
    delta_width = max(len(headers[2]), len("+0.00"))
    lines = [f"Prompt: {prompt_name}"]
    bar_width = 12
    metric_width = max(
        max(len(header) for header in headers[3:]), len(f"0.00 {'#' * bar_width}")
    )
    header_line = " ".join(
        [
            f"{headers[0]:<{model_width}}",
            f"{headers[1]:>{secs_width}}",
            f"{headers[2]:>{delta_width}}",
            f"{headers[3]:<{metric_width}}",
            f"{headers[4]:<{metric_width}}",
            f"{headers[5]:<{metric_width}}",
        ]
    )
    lines.append(header_line)
    lines.append(
        " ".join(
            [
                "-" * model_width,
                "-" * secs_width,
                "-" * delta_width,
                "-" * metric_width,
                "-" * metric_width,
                "-" * metric_width,
            ]
        )
    )
    for model, seconds, mirage, grounding, redundancy in rows:
        delta = seconds - baseline_seconds
        delta_str = f"{delta:+.2f}"
        lines.append(
            " ".join(
                [
                    f"{model:<{model_width}}",
                    f"{seconds:>{secs_width}.2f}",
                    f"{delta_str:>{delta_width}}",
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
    run_start = time.monotonic()
    print(f"\nRunning prompt: {prompt_name}", flush=True)
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
    error_models: List[str] = []
    response_outputs: List[tuple[str, str, bool]] = [
        ("gpt-5-nano", baseline_content.strip(), True)
    ]

    selected_models = _select_benchmark_models()
    total_models = len(selected_models)
    completed = 1  # baseline already done
    _print_progress(completed, total_models, time.monotonic() - run_start)

    for model in selected_models:
        if model == "gpt-5-nano":
            continue  # Already processed as baseline
        start_time = time.monotonic()
        try:
            response = chat(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                format=ResumeProjectSummary.model_json_schema(),
                options={"temperature": 0},
            )
        except Exception as exc:
            elapsed = time.monotonic() - start_time
            error_models.append(f"{model} ({exc})")
            response_outputs.append((model, "", False))
            completed += 1
            print(
                f"Done {model} in {elapsed:.2f}s (error). "
                f"Total elapsed {time.monotonic() - run_start:.1f}s",
                flush=True,
            )
            _print_progress(completed, total_models, time.monotonic() - run_start)
            continue

        elapsed = time.monotonic() - start_time

        message_content = response.message.content
        if not message_content:
            invalid_models.append(f"{model} (empty response)")
            response_outputs.append((model, "", False))
            completed += 1
            print(
                f"Done {model} in {elapsed:.2f}s (empty). "
                f"Total elapsed {time.monotonic() - run_start:.1f}s",
                flush=True,
            )
            _print_progress(completed, total_models, time.monotonic() - run_start)
            continue

        is_valid = True
        try:
            parsed = ResumeProjectSummary.model_validate_json(message_content)
        except ValidationError:
            invalid_models.append(model)
            is_valid = False

        response_outputs.append((model, message_content.strip(), is_valid))

        completed += 1
        status = "ok" if is_valid else "invalid JSON"
        print(
            f"Done {model} in {elapsed:.2f}s ({status}). "
            f"Total elapsed {time.monotonic() - run_start:.1f}s"
            ,
            flush=True,
        )
        _print_progress(completed, total_models, time.monotonic() - run_start)

        if not is_valid:
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

    output_lines: List[str] = []
    output_lines.append(_render_table(prompt_name, rows, baseline_seconds))

    top_candidates = sorted(candidates, key=lambda item: item[4], reverse=True)[:3]
    output_lines.append("Top 3 responses:")
    for rank, (model, mirage, grounding, redundancy, score, content) in enumerate(
        top_candidates, start=1
    ):
        output_lines.extend(
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

    if invalid_models:
        output_lines.append(f"Invalid JSON outputs: {', '.join(invalid_models)}")
    if error_models:
        output_lines.append(f"Errored models: {', '.join(error_models)}")

    output_text = "\n".join(output_lines)
    print(output_text)

    md_lines = list(output_lines)
    md_lines.append("All responses:")
    for model, content, is_valid in response_outputs:
        status = "valid JSON" if is_valid else "invalid JSON"
        md_lines.extend([f"{model} ({status})", content, "---"])

    report_path = Path(__file__).resolve().parents[2] / "docs" / "ollama-benchmark.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(md_lines))
        handle.write("\n\n")
