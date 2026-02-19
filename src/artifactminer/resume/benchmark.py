"""
Model Benchmark — Compare local GGUF models on resume generation tasks.

Runs identical prompts through each model and measures:
- Inference speed (tokens/second)
- Peak memory usage
- Structured output reliability
- Output quality (side-by-side for human review)

Usage:
    resume benchmark
    resume benchmark --models qwen3-1.7b lfm2.5-1.2b
"""

from __future__ import annotations

import json
import resource
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel

from .llm_client import (
    ensure_model_available,
    get_model,
    unload_model,
    query_llm,
    query_llm_text,
)


# ---------------------------------------------------------------------------
# Benchmark prompts — representative resume generation tasks
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You are a professional resume writer. Be concise and factual. "
    "Use action verbs. Each bullet should be 1-2 lines max."
)

# Prompt 1: Project bullet generation (text output)
TEXT_PROMPT = """Based on the following project facts, write 3-5 resume bullet points:

PROJECT: capstone-project-team-1
Stack: Python (65%), JavaScript (20%), TypeScript (15%)
Frameworks: FastAPI, SQLAlchemy, pytest, React
Contribution: 45% of commits (120/267)
Period: 2024-09-01 to 2025-02-05
Work breakdown: code: 78%, tests: 12%, docs: 8%, config: 2%
Skills demonstrated: REST API Design, Asynchronous Programming, Data Validation
Key insights:
  - API design and architecture: Clean API design with validation and DI

Write the bullet points now (no preamble, just bullets starting with •):"""


# Prompt 2: Commit classification (structured output)
class CommitClassification(BaseModel):
    classifications: list[dict]  # [{hash, category}]


STRUCTURED_PROMPT = """Classify each commit message into one category: feature, bugfix, refactor, test, docs, or chore.

Commits:
1. abc1234: Add user authentication with JWT tokens
2. def5678: Fix null pointer in login handler
3. ghi9012: Extract validation logic to separate module
4. jkl3456: Add unit tests for auth middleware
5. mno7890: Update README with setup instructions
6. pqr1234: Bump FastAPI from 0.104 to 0.110

Return JSON with a "classifications" array containing objects with "hash" and "category" fields."""


# Prompt 3: Skill timeline narrative (text output)
TIMELINE_PROMPT = """Generate a 2-sentence skill evolution narrative from this chronological data:

- 2024-01: Python (first commit)
- 2024-03: FastAPI, SQLAlchemy (backend work starts)
- 2024-05: pytest (testing adoption)
- 2024-07: React, TypeScript (frontend work begins)
- 2024-09: Docker, CI/CD (deployment pipeline)
- 2024-11: Async patterns, WebSockets (performance optimization)

Write a concise narrative showing technical growth over time:"""


# ---------------------------------------------------------------------------
# Benchmark data structures
# ---------------------------------------------------------------------------


@dataclass
class RunResult:
    """Result of a single benchmark run."""
    prompt_name: str
    model: str
    output: str
    elapsed_seconds: float
    tokens_generated: int
    tokens_per_second: float
    parse_success: bool = True  # For structured output
    error: Optional[str] = None


@dataclass
class ModelBenchmark:
    """Aggregated results for a single model."""
    model: str
    runs: List[RunResult] = field(default_factory=list)
    peak_memory_mb: float = 0.0
    load_time_seconds: float = 0.0

    @property
    def avg_tokens_per_second(self) -> float:
        successful = [r for r in self.runs if not r.error]
        if not successful:
            return 0.0
        return sum(r.tokens_per_second for r in successful) / len(successful)

    @property
    def structured_success_rate(self) -> float:
        structured = [r for r in self.runs if r.prompt_name == "structured"]
        if not structured:
            return 0.0
        return sum(1 for r in structured if r.parse_success) / len(structured)


# ---------------------------------------------------------------------------
# Benchmark execution
# ---------------------------------------------------------------------------


def _get_memory_mb() -> float:
    """Get current process peak memory in MB."""
    usage = resource.getrusage(resource.RUSAGE_SELF)
    # ru_maxrss is in bytes on macOS
    return usage.ru_maxrss / (1024 * 1024)


def _run_text_prompt(
    model: str, prompt_name: str, prompt: str, system: str | None = None
) -> RunResult:
    """Run a text prompt and measure performance."""
    start = time.perf_counter()
    try:
        output = query_llm_text(
            prompt, model=model, system=system, temperature=0.3, max_tokens=512
        )
        elapsed = time.perf_counter() - start
        # Rough token estimate: ~0.75 tokens per word
        tokens = int(len(output.split()) * 1.3)
        return RunResult(
            prompt_name=prompt_name,
            model=model,
            output=output,
            elapsed_seconds=elapsed,
            tokens_generated=tokens,
            tokens_per_second=tokens / elapsed if elapsed > 0 else 0,
        )
    except Exception as e:
        elapsed = time.perf_counter() - start
        return RunResult(
            prompt_name=prompt_name,
            model=model,
            output="",
            elapsed_seconds=elapsed,
            tokens_generated=0,
            tokens_per_second=0,
            error=str(e),
        )


def _run_structured_prompt(model: str) -> RunResult:
    """Run the structured output prompt and measure performance."""
    start = time.perf_counter()
    try:
        result = query_llm(
            STRUCTURED_PROMPT,
            CommitClassification,
            model=model,
            temperature=0.1,
        )
        elapsed = time.perf_counter() - start
        output = json.dumps(result.model_dump(), indent=2)
        tokens = int(len(output.split()) * 1.3)
        return RunResult(
            prompt_name="structured",
            model=model,
            output=output,
            elapsed_seconds=elapsed,
            tokens_generated=tokens,
            tokens_per_second=tokens / elapsed if elapsed > 0 else 0,
            parse_success=True,
        )
    except Exception as e:
        elapsed = time.perf_counter() - start
        return RunResult(
            prompt_name="structured",
            model=model,
            output="",
            elapsed_seconds=elapsed,
            tokens_generated=0,
            tokens_per_second=0,
            parse_success=False,
            error=str(e),
        )


def benchmark_model(model: str, runs: int = 3) -> ModelBenchmark:
    """Run the full benchmark suite for a model."""
    result = ModelBenchmark(model=model)

    # Ensure model is downloaded
    print(f"\n{'='*60}")
    print(f"Benchmarking: {model}")
    print(f"{'='*60}")

    ensure_model_available(model)

    # Measure model load time
    unload_model(model)
    mem_before = _get_memory_mb()
    start = time.perf_counter()
    get_model(model)
    result.load_time_seconds = time.perf_counter() - start
    result.peak_memory_mb = _get_memory_mb() - mem_before
    print(f"  Load time: {result.load_time_seconds:.2f}s")
    print(f"  Memory delta: {result.peak_memory_mb:.0f} MB")

    # Run text prompts
    for i in range(runs):
        label = "cold" if i == 0 else f"warm-{i}"
        print(f"\n  Run {i+1}/{runs} ({label}):")

        # Bullet generation
        run = _run_text_prompt(model, "bullets", TEXT_PROMPT, SYSTEM_PROMPT)
        result.runs.append(run)
        status = f"{run.tokens_per_second:.1f} tok/s" if not run.error else f"ERROR: {run.error}"
        print(f"    bullets: {run.elapsed_seconds:.2f}s — {status}")

        # Timeline narrative
        run = _run_text_prompt(model, "timeline", TIMELINE_PROMPT, SYSTEM_PROMPT)
        result.runs.append(run)
        status = f"{run.tokens_per_second:.1f} tok/s" if not run.error else f"ERROR: {run.error}"
        print(f"    timeline: {run.elapsed_seconds:.2f}s — {status}")

        # Structured output
        run = _run_structured_prompt(model)
        result.runs.append(run)
        status = f"{'OK' if run.parse_success else 'FAIL'} — {run.elapsed_seconds:.2f}s"
        print(f"    structured: {status}")

    # Unload to free memory for next model
    unload_model(model)

    return result


def generate_report(benchmarks: List[ModelBenchmark]) -> str:
    """Generate a markdown comparison report."""
    lines = ["# Model Benchmark Report", ""]

    # Summary table
    lines.append("## Summary")
    lines.append("")
    lines.append("| Model | Load Time | Memory | Avg tok/s | Structured OK | ")
    lines.append("|-------|-----------|--------|-----------|---------------|")
    for b in benchmarks:
        lines.append(
            f"| {b.model} | {b.load_time_seconds:.2f}s | "
            f"{b.peak_memory_mb:.0f} MB | "
            f"{b.avg_tokens_per_second:.1f} | "
            f"{b.structured_success_rate:.0%} |"
        )
    lines.append("")

    # Detailed results per model
    for b in benchmarks:
        lines.append(f"## {b.model}")
        lines.append("")

        # Group by prompt name
        by_prompt: dict[str, list[RunResult]] = {}
        for run in b.runs:
            by_prompt.setdefault(run.prompt_name, []).append(run)

        for prompt_name, runs in by_prompt.items():
            lines.append(f"### {prompt_name}")
            lines.append("")
            for i, run in enumerate(runs):
                label = "cold" if i == 0 else f"warm-{i}"
                lines.append(f"**Run {i+1} ({label}):** {run.elapsed_seconds:.2f}s")
                if run.error:
                    lines.append(f"  Error: {run.error}")
                else:
                    lines.append(f"```\n{run.output[:500]}\n```")
                lines.append("")

    return "\n".join(lines)


def run_benchmark(
    models: List[str] | None = None,
    runs: int = 3,
    output_path: str | None = None,
) -> str:
    """
    Run the full benchmark and return the report.

    Args:
        models: List of model names to benchmark. Defaults to all registry models.
        runs: Number of runs per prompt (1 cold + N-1 warm).
        output_path: Optional path to save the markdown report.

    Returns:
        Markdown report string.
    """
    from .llm_client import MODEL_REGISTRY

    if models is None:
        models = list(MODEL_REGISTRY.keys())

    benchmarks = []
    for model in models:
        benchmarks.append(benchmark_model(model, runs=runs))

    report = generate_report(benchmarks)

    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(report)
        print(f"\nReport saved to: {path}")

    return report
