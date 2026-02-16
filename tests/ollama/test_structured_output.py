"""Benchmarks structured JSON output from Ollama models."""

from __future__ import annotations

import time
import sys
from pathlib import Path
from typing import List

import pytest
from ollama import chat, list as ollama_list
from pydantic import BaseModel, Field

MODULE_DIR = Path(__file__).resolve().parent
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from structured_output_common import select_small_models

# Configurable benchmark model list
BENCHMARK_MODELS: List[str] = [
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
MAX_MODEL_SIZE_B: float = 7.0

PROJECT_SNAPSHOT = """
Project: Campus Resource Tracker

Files:
- README.md: Web app to help students log study spaces, equipment loans, and lab availability.
- src/api/routes.py: FastAPI endpoints for spaces, availability, and reservations.
- src/services/availability.py: Caches live availability with TTL and retries.
- src/db/models.py: SQLAlchemy models for spaces, reservations, and users.
- src/ui/Dashboard.tsx: React dashboard with filters, calendar view, and alerts.
- src/ui/components/UsageChart.tsx: D3-based chart for weekly utilization.
- tests/api/test_availability.py: Validates API responses and error handling.
- tests/ui/test_dashboard.py: Covers filtering behavior and empty states.

Notable changes:
- Added caching to reduce API latency and rate limits.
- Added audit logging for reservation updates.
- Improved error messages and validation for booking conflicts.
"""


class ResumeProjectSummary(BaseModel):
    project_name: str = Field(..., description="Project name.")
    one_liner: str = Field(..., description="Resume-ready single sentence.")
    highlights: List[str] = Field(..., description="3-5 resume-worthy bullet points.")
    skills: List[str] = Field(..., description="Technical skills demonstrated.")


def _build_prompt() -> str:
    return (
        "You are summarizing a student project for a resume. "
        "Return only JSON that matches the provided schema. "
        "Keep it concise, factual, and positive. "
        "Use the project snapshot below.\n\n"
        f"{PROJECT_SNAPSHOT}"
    )


def _select_benchmark_models() -> List[str]:
    """Select models from BENCHMARK_MODELS, filtered by installation and size limit.
    
    Checks installation status and applies MAX_MODEL_SIZE_B filter.
    """
    available = {m.model for m in ollama_list().models}
    candidates = list(BENCHMARK_MODELS)
    
    if MAX_MODEL_SIZE_B > 0.0:
        # Apply size limit
        candidates = select_small_models(candidates, max_b=MAX_MODEL_SIZE_B)
    
    # Only include models that are actually installed
    selected = [m for m in candidates if m in available]
    
    if not selected:
        pytest.skip("No models from BENCHMARK_MODELS are available.")
    
    return selected


@pytest.mark.parametrize("model", _select_benchmark_models())
def test_structured_output_benchmark(model: str) -> None:
    prompt = _build_prompt()

    timings: List[float] = []
    last_parsed: ResumeProjectSummary | None = None

    for _ in range(2):
        start_time = time.monotonic()
        response = chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            format=ResumeProjectSummary.model_json_schema(),
            options={"temperature": 0},
        )
        timings.append(time.monotonic() - start_time)

        message_content = response.message.content
        assert message_content, "Ollama response content was empty."

        parsed = ResumeProjectSummary.model_validate_json(message_content)
        assert parsed.project_name.strip()
        assert parsed.one_liner.strip()
        assert parsed.highlights
        assert parsed.skills

        last_parsed = parsed

    cold_seconds, warm_seconds = timings
    print(
        "\n".join(
            [
                f"Model: {model}",
                f"Cold seconds: {cold_seconds:.2f}",
                f"Warm seconds: {warm_seconds:.2f}",
                "---",
            ]
        )
    )
    # if last_parsed is not None:
    #     print(last_parsed.model_dump_json(indent=2))
