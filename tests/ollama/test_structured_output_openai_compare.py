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


@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY")
    or os.getenv("OPENAI_API_KEY") == "your_openai_api_key_here",
    reason="OPENAI_API_KEY not set in environment or using placeholder value",
)
@pytest.mark.parametrize("prompt_name,prompt", prompt_variants())
def test_structured_output_openai_compare(prompt_name: str, prompt: str) -> None:
    baseline_content = get_gpt5_nano_response_sync(prompt)
    assert baseline_content, "OpenAI response content was empty."

    baseline_parsed = ResumeProjectSummary.model_validate_json(baseline_content)
    assert baseline_parsed.project_name.strip()
    assert baseline_parsed.one_liner.strip()
    assert baseline_parsed.highlights
    assert baseline_parsed.skills

    openai_mirage, openai_grounding, openai_redundancy = _metrics(baseline_parsed)

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

        print(
            "\n".join(
                [
                    f"Model: {model}",
                    f"Prompt: {prompt_name}",
                    "Baseline: gpt-5-nano",
                    f"Seconds: {elapsed:.2f}",
                    f"Mirage rate: {mirage_rate:.2f} (delta {mirage_rate - openai_mirage:+.2f})",
                    f"Entity grounding rate: {grounding_rate:.2f} (delta {grounding_rate - openai_grounding:+.2f})",
                    f"Redundancy rate: {redundancy_rate:.2f} (delta {redundancy_rate - openai_redundancy:+.2f})",
                    "---",
                ]
            )
        )
