"""
LLM query runner — executes prompts and parses structured responses.

Handles:
  - Calling query_llm_text with the right system prompt
  - Parsing DESCRIPTION/BULLETS/NARRATIVE output format
  - Progress reporting via callback
"""

from __future__ import annotations

import logging
import re
from typing import Callable, Optional

from ..models import (
    ProjectDataBundle,
    PortfolioDataBundle,
    ProjectSection,
)
from .prompts import (
    PROJECT_SYSTEM,
    SUMMARY_SYSTEM,
    build_project_prompt,
    build_summary_prompt,
    build_skills_prompt,
    build_profile_prompt,
)

log = logging.getLogger(__name__)


def _query(
    prompt: str,
    model: str,
    system: str,
) -> str:
    """Execute a single LLM query, returning raw text."""
    from ..llm_client import query_llm_text

    return query_llm_text(
        prompt=prompt,
        model=model,
        system=system,
        temperature=0.3,
    )


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------


def _parse_project_response(text: str) -> ProjectSection:
    """
    Parse the structured DESCRIPTION/BULLETS/NARRATIVE response.

    Falls back gracefully if the model doesn't follow the format exactly.
    """
    section = ProjectSection()

    # Extract DESCRIPTION
    desc_match = re.search(r"DESCRIPTION:\s*(.+?)(?=\nBULLETS:|\Z)", text, re.S)
    if desc_match:
        section.description = desc_match.group(1).strip()

    # Extract BULLETS
    bullets_match = re.search(r"BULLETS:\s*(.+?)(?=\nNARRATIVE:|\Z)", text, re.S)
    if bullets_match:
        bullets_text = bullets_match.group(1)
        for line in bullets_text.split("\n"):
            line = line.strip()
            if line and (line.startswith("-") or line.startswith("•") or line.startswith("*")):
                bullet = line.lstrip("-•* ").strip()
                if bullet:
                    section.bullets.append(bullet)

    # Extract NARRATIVE
    narr_match = re.search(r"NARRATIVE:\s*(.+)", text, re.S)
    if narr_match:
        section.narrative = narr_match.group(1).strip()

    # Fallback: if no structured sections found, treat whole response as bullets
    if not section.bullets and not section.description:
        for line in text.split("\n"):
            line = line.strip()
            if line and (line.startswith("-") or line.startswith("•") or line.startswith("*")):
                bullet = line.lstrip("-•* ").strip()
                if bullet:
                    section.bullets.append(bullet)
        if not section.bullets:
            # Last resort: use entire response as description
            section.description = text.strip()[:500]

    return section


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_project_query(
    bundle: ProjectDataBundle,
    model: str,
    *,
    progress: Optional[Callable[[str], None]] = None,
) -> ProjectSection:
    """
    Run the LLM query for a single project and return parsed sections.

    Raises RuntimeError if the LLM returns an empty response.
    """
    if progress:
        progress(f"  Querying LLM for {bundle.project_name}...")

    prompt = build_project_prompt(bundle)
    response = _query(prompt, model, PROJECT_SYSTEM)

    if not response.strip():
        raise RuntimeError(
            f"LLM returned empty response for project {bundle.project_name}"
        )

    return _parse_project_response(response)


def run_portfolio_queries(
    portfolio: PortfolioDataBundle,
    model: str,
    *,
    progress: Optional[Callable[[str], None]] = None,
) -> tuple[str, str, str]:
    """
    Run the three portfolio-level LLM queries.

    Returns (professional_summary, skills_section, developer_profile).
    """
    # 1. Professional summary
    if progress:
        progress("Generating professional summary...")
    summary_prompt = build_summary_prompt(portfolio)
    summary = _query(summary_prompt, model, SUMMARY_SYSTEM).strip()

    # 2. Skills section
    if progress:
        progress("Generating skills section...")
    skills_prompt = build_skills_prompt(portfolio)
    skills = _query(skills_prompt, model, SUMMARY_SYSTEM).strip()

    # 3. Developer profile
    if progress:
        progress("Generating developer profile...")
    profile_prompt = build_profile_prompt(portfolio)
    profile = _query(profile_prompt, model, SUMMARY_SYSTEM).strip()

    return summary, skills, profile
