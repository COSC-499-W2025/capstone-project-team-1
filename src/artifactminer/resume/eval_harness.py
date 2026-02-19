"""Evaluation harness for the multi-stage local-LLM resume pipeline."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any, Callable, Optional

from .assembler import assemble_markdown
from .models import UserFeedback
from .pipeline import generate_resume_v3_multistage


@dataclass
class EvalRunResult:
    """Single evaluation run summary."""

    run_index: int
    stage: str
    generation_time_seconds: float
    models_used: list[str]
    errors: list[str]
    schema: dict[str, Any]
    citations: dict[str, Any]
    prose: dict[str, Any]
    markdown_path: str
    json_path: str


def _build_default_feedback() -> UserFeedback:
    """Force stage 3 for evaluation with neutral polish instructions."""
    return UserFeedback(
        general_notes="Polish for clarity and consistency while preserving factual grounding.",
        tone="concise and technical",
    )


def _write_markdown_report(payload: dict[str, Any], path: Path) -> None:
    """Write a compact markdown report for quick review."""
    aggregate = payload["aggregate"]
    runs = payload["runs"]

    lines: list[str] = []
    lines.append("# Multi-stage Evaluation Report")
    lines.append("")
    lines.append(f"Generated at: {payload['generated_at']}")
    lines.append("")
    lines.append("## Aggregate")
    lines.append("")
    lines.append(f"- Runs: {aggregate['runs']}")
    lines.append(
        f"- Avg generation time: {aggregate['avg_generation_time_seconds']:.2f}s"
    )
    lines.append(f"- Avg citation precision: {aggregate['avg_citation_precision']:.4f}")
    lines.append(f"- Avg fact coverage: {aggregate['avg_fact_coverage']:.4f}")
    lines.append(f"- Avg repaired bullets: {aggregate['avg_repaired_bullets']:.2f}")
    lines.append(
        f"- Avg repetition ratio: {aggregate.get('avg_repetition_ratio', 0.0):.4f}"
    )
    lines.append(
        f"- Avg low-signal bullets: {aggregate.get('avg_low_signal_bullets', 0.0):.2f}"
    )
    lines.append(f"- Avg prose leaks: {aggregate.get('avg_prose_leaks', 0.0):.2f}")
    lines.append("")
    lines.append("## Per-run")
    lines.append("")

    for run in runs:
        lines.append(f"### Run {run['run_index']}")
        lines.append(f"- Stage: {run['stage']}")
        lines.append(f"- Time: {run['generation_time_seconds']:.2f}s")
        lines.append(f"- Models: {', '.join(run['models_used'])}")
        lines.append(
            f"- Citation precision: {run['citations'].get('citation_precision', 0.0):.4f}"
        )
        lines.append(
            f"- Fact coverage: {run['citations'].get('fact_coverage', 0.0):.4f}"
        )
        lines.append(
            f"- Repaired bullets: {run['citations'].get('repaired_bullets', 0)}"
        )
        prose = run.get("prose", {})
        lines.append(
            f"- Repetition ratio: {float(prose.get('repetition_ratio', 0.0)):.4f}"
        )
        lines.append(f"- Low-signal bullets: {int(prose.get('low_signal_bullets', 0))}")
        leak_count = int(prose.get("meta_preamble_hits", 0)) + int(
            prose.get("note_leaks", 0)
        )
        lines.append(f"- Prose leaks: {leak_count}")
        lines.append(f"- Schema stats: {json.dumps(run['schema'], sort_keys=True)}")
        if run["errors"]:
            lines.append(f"- Errors: {len(run['errors'])}")
        lines.append("")

    path.write_text("\n".join(lines))


def evaluate_multistage_pipeline(
    zip_path: str,
    user_email: str,
    *,
    runs: int = 1,
    stage1_model: str = "qwen2.5-coder-3b-q4",
    stage2_model: str = "lfm2.5-1.2b-bf16",
    stage3_model: str = "lfm2.5-1.2b-bf16",
    output_dir: str = "resume_output/eval",
    progress_callback: Optional[Callable[[str], None]] = None,
) -> dict[str, Any]:
    """Run the multi-stage pipeline repeatedly and collect quality metrics."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_results: list[EvalRunResult] = []

    def prog(msg: str) -> None:
        if progress_callback:
            progress_callback(msg)

    for run_idx in range(1, runs + 1):
        prog(f"[eval] Run {run_idx}/{runs}: starting")
        result = generate_resume_v3_multistage(
            zip_path=zip_path,
            user_email=user_email,
            stage1_model=stage1_model,
            stage2_model=stage2_model,
            stage3_model=stage3_model,
            user_feedback=_build_default_feedback(),  # force Stage 3 during eval
            progress_callback=progress_callback,
        )

        run_md_path = out_dir / f"run-{run_idx:02d}-final.md"
        run_json_path = out_dir / f"run-{run_idx:02d}-metrics.json"
        run_md_path.write_text(assemble_markdown(result))

        schema = dict(result.quality_metrics.get("schema", {}))
        citations = dict(result.quality_metrics.get("citations", {}))
        prose = dict(result.quality_metrics.get("prose", {}))
        run_payload = {
            "stage": result.stage,
            "generation_time_seconds": result.generation_time_seconds,
            "models_used": result.models_used,
            "errors": result.errors,
            "schema": schema,
            "citations": citations,
            "prose": prose,
        }
        run_json_path.write_text(json.dumps(run_payload, indent=2, default=str))

        run_results.append(
            EvalRunResult(
                run_index=run_idx,
                stage=result.stage,
                generation_time_seconds=result.generation_time_seconds,
                models_used=list(result.models_used),
                errors=list(result.errors),
                schema=schema,
                citations=citations,
                prose=prose,
                markdown_path=str(run_md_path),
                json_path=str(run_json_path),
            )
        )
        prog(f"[eval] Run {run_idx}/{runs}: complete")

    avg_time = (
        mean(r.generation_time_seconds for r in run_results) if run_results else 0.0
    )
    avg_citation_precision = (
        mean(float(r.citations.get("citation_precision", 0.0)) for r in run_results)
        if run_results
        else 0.0
    )
    avg_fact_coverage = (
        mean(float(r.citations.get("fact_coverage", 0.0)) for r in run_results)
        if run_results
        else 0.0
    )
    avg_repaired = (
        mean(float(r.citations.get("repaired_bullets", 0.0)) for r in run_results)
        if run_results
        else 0.0
    )
    avg_repetition_ratio = (
        mean(float(r.prose.get("repetition_ratio", 0.0)) for r in run_results)
        if run_results
        else 0.0
    )
    avg_low_signal_bullets = (
        mean(float(r.prose.get("low_signal_bullets", 0.0)) for r in run_results)
        if run_results
        else 0.0
    )
    avg_prose_leaks = (
        mean(
            float(r.prose.get("meta_preamble_hits", 0.0))
            + float(r.prose.get("note_leaks", 0.0))
            for r in run_results
        )
        if run_results
        else 0.0
    )

    payload = {
        "generated_at": datetime.now().isoformat(),
        "config": {
            "zip_path": zip_path,
            "user_email": user_email,
            "runs": runs,
            "stage1_model": stage1_model,
            "stage2_model": stage2_model,
            "stage3_model": stage3_model,
        },
        "aggregate": {
            "runs": len(run_results),
            "avg_generation_time_seconds": avg_time,
            "avg_citation_precision": avg_citation_precision,
            "avg_fact_coverage": avg_fact_coverage,
            "avg_repaired_bullets": avg_repaired,
            "avg_repetition_ratio": avg_repetition_ratio,
            "avg_low_signal_bullets": avg_low_signal_bullets,
            "avg_prose_leaks": avg_prose_leaks,
        },
        "runs": [asdict(r) for r in run_results],
    }

    summary_json = out_dir / f"evaluation-{timestamp}.json"
    summary_md = out_dir / f"evaluation-{timestamp}.md"
    summary_json.write_text(json.dumps(payload, indent=2, default=str))
    _write_markdown_report(payload, summary_md)

    payload["report_paths"] = {
        "json": str(summary_json),
        "markdown": str(summary_md),
    }
    return payload
