"""
LLM Enhancement Module - Optional single-call LLM for prose polishing.

This module provides OPTIONAL LLM enhancement. The key principles:

1. LLM receives ONLY pre-digested facts, never raw code
2. ONE call per portfolio (not per file, not per project)
3. Works with ANY Ollama model the user has installed
4. Graceful degradation if Ollama is unavailable

The LLM's job is simple: take structured facts and write compelling prose.
It is NOT doing code analysis - that's already done by static analysis.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .facts import PortfolioFacts, ProjectFacts
from .llm_client import (
    query_llm_text,
    check_llm_available,
    get_available_models,
)


@dataclass
class ResumeContent:
    """Generated resume content - works with or without LLM."""

    # Per-project content
    project_bullets: dict[str, List[str]]  # project_name -> bullet points

    # Portfolio-level content
    professional_summary: Optional[str] = None
    skills_section: Optional[str] = None

    # New portfolio-level sections
    skill_evolution: Optional[str] = None
    developer_profile: Optional[str] = None
    complexity_highlights: Optional[str] = None
    work_breakdown: Optional[dict] = None  # {"feature": 15, "bugfix": 8, ...}

    # Metadata
    llm_enhanced: bool = False
    model_used: Optional[str] = None


def _query_llm(prompt: str, model: str, system: Optional[str] = None) -> Optional[str]:
    """
    Query the local LLM for text output.

    Args:
        prompt: The prompt to send
        model: Model name (e.g., "qwen3-1.7b", "lfm2.5-1.2b")
        system: Optional system prompt

    Returns:
        Response text, or None if failed
    """
    try:
        return query_llm_text(
            prompt=prompt,
            model=model,
            system=system,
            temperature=0.3,
        )
    except Exception as e:
        print(f"[enhance] LLM query failed: {e}")
        return None


# ---------------------------------------------------------------------------
# Prompt Construction
# ---------------------------------------------------------------------------

SYSTEM_CONTEXT = """You are a professional resume writer. Your job is to transform
technical project facts into compelling, recruiter-friendly resume bullet points.

Rules:
- Be CONCISE: each bullet should be 1-2 lines max
- Be FACTUAL: only mention what's in the provided facts, never invent
- Be SPECIFIC: use actual technology names, not vague terms
- Use ACTION VERBS: Built, Designed, Implemented, Developed, Created
- QUANTIFY when possible: contribution percentages, commit counts
- Focus on IMPACT and SKILLS demonstrated

Output format: Write bullet points directly, no explanations or preamble."""


def build_project_prompt(project: ProjectFacts) -> str:
    """Build a prompt for generating bullets for a single project."""
    context = project.to_llm_context()

    return f"""{SYSTEM_CONTEXT}

Based on the following project facts, write 3-5 resume bullet points:

{context}

Write the bullet points now (no preamble, just bullets starting with •):"""


def build_portfolio_prompt(portfolio: PortfolioFacts) -> str:
    """Build a prompt for the full portfolio summary."""
    context = portfolio.to_llm_context()

    return f"""{SYSTEM_CONTEXT}

Based on the following portfolio of projects, write:
1. A 2-3 sentence professional summary suitable for the top of a resume
2. A skills section grouping the demonstrated technical skills by category

Portfolio facts:
{context}

Format your response as:
SUMMARY:
[Your 2-3 sentence summary here]

SKILLS:
[Grouped skills here]"""


# ---------------------------------------------------------------------------
# Template Fallback (No LLM)
# ---------------------------------------------------------------------------

def generate_template_bullets(project: ProjectFacts) -> List[str]:
    """
    Generate resume bullets using templates (no LLM required).

    This provides a baseline that works on any machine. The bullets are
    factual and structured, just not as polished as LLM-enhanced versions.
    """
    bullets = []

    # Contribution bullet
    if project.user_contribution_pct and project.user_contribution_pct > 0:
        contrib = f"{project.user_contribution_pct:.0f}%"
        stack = project.primary_language or "the codebase"
        if project.frameworks:
            stack = f"{project.frameworks[0]}/{project.primary_language or 'application'}"
        bullets.append(
            f"Contributed {contrib} of commits to {project.project_name}, "
            f"a {stack} project"
        )

    # Skills bullet
    if project.detected_skills:
        top_skills = project.detected_skills[:4]
        bullets.append(
            f"Demonstrated proficiency in {', '.join(top_skills)}"
        )

    # Framework/technology bullet
    if project.frameworks:
        frameworks_str = ", ".join(project.frameworks[:3])
        bullets.append(f"Built features using {frameworks_str}")

    # Insights bullet
    if project.insights:
        insight = project.insights[0]
        title = insight.get("title", "")
        if title:
            bullets.append(f"Applied {title.lower()} principles in implementation")

    # Activity breakdown bullet
    if project.activity_breakdown:
        test_pct = project.activity_breakdown.get("tests", 0)
        if test_pct > 10:
            bullets.append(f"Wrote comprehensive tests ({test_pct:.0f}% of contributions)")

    return bullets if bullets else [f"Contributed to {project.project_name}"]


def generate_template_summary(portfolio: PortfolioFacts) -> str:
    """Generate a professional summary using templates (no LLM)."""
    parts = []

    # Experience statement
    if portfolio.total_projects > 0:
        parts.append(
            f"Software developer with hands-on experience across "
            f"{portfolio.total_projects} project{'s' if portfolio.total_projects > 1 else ''}"
        )

    # Top languages
    if portfolio.languages_used:
        top_langs = portfolio.languages_used[:3]
        # Clean up file extensions to language names
        lang_names = []
        ext_to_name = {
            ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
            ".java": "Java", ".go": "Go", ".rs": "Rust", ".cpp": "C++",
            ".c": "C", ".rb": "Ruby", ".php": "PHP", ".kt": "Kotlin",
        }
        for ext in top_langs:
            lang_names.append(ext_to_name.get(ext, ext.replace(".", "")))
        parts.append(f"Proficient in {', '.join(lang_names)}")

    # Top frameworks
    if portfolio.frameworks_used:
        top_fw = portfolio.frameworks_used[:4]
        parts.append(f"with experience in {', '.join(top_fw)}")

    return ". ".join(parts) + "." if parts else "Software developer."


def generate_template_skills(portfolio: PortfolioFacts) -> str:
    """Generate a skills section using templates (no LLM)."""
    sections = []

    # Languages
    if portfolio.languages_used:
        ext_to_name = {
            ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
            ".java": "Java", ".go": "Go", ".rs": "Rust", ".cpp": "C++",
            ".c": "C", ".rb": "Ruby", ".php": "PHP", ".kt": "Kotlin",
        }
        lang_names = [ext_to_name.get(ext, ext.replace(".", "")) for ext in portfolio.languages_used[:6]]
        sections.append(f"Languages: {', '.join(lang_names)}")

    # Frameworks
    if portfolio.frameworks_used:
        sections.append(f"Frameworks: {', '.join(portfolio.frameworks_used[:6])}")

    # Technical skills
    if portfolio.top_skills:
        sections.append(f"Technical Skills: {', '.join(portfolio.top_skills[:8])}")

    return "\n".join(sections)


# ---------------------------------------------------------------------------
# Main Enhancement Functions
# ---------------------------------------------------------------------------

def enhance_with_llm(
    portfolio: PortfolioFacts,
    model: str = "qwen3-1.7b",
) -> ResumeContent:
    """
    Enhance portfolio facts with LLM-generated prose.

    Args:
        portfolio: Pre-built PortfolioFacts from static analysis
        model: Ollama model to use

    Returns:
        ResumeContent with generated bullets and summaries

    Raises:
        RuntimeError: If Ollama is not available or model is not found
    """
    result = ResumeContent(
        project_bullets={},
        llm_enhanced=False,
    )

    # Check if model is available
    if not check_llm_available(model):
        raise RuntimeError(
            f"Model '{model}' is not available. "
            f"Run 'resume download-model {model}' to download it."
        )

    # List available models for diagnostics if needed
    available = get_available_models()

    print(f"[enhance] Using model: {model}")

    # Generate bullets for each project
    for project in portfolio.projects:
        prompt = build_project_prompt(project)
        response = _query_llm(prompt, model)

        if not response:
            raise RuntimeError(f"LLM failed to generate bullets for {project.project_name}")

        # Parse bullets from response
        bullets = []
        for line in response.split("\n"):
            line = line.strip()
            if line and (line.startswith("•") or line.startswith("-") or line.startswith("*")):
                # Clean up the bullet marker
                bullet = line.lstrip("•-* ").strip()
                if bullet:
                    bullets.append(bullet)

        if not bullets:
            raise RuntimeError(
                f"LLM response for {project.project_name} contained no bullets. "
                f"Response was: {response[:200]}..."
            )

        result.project_bullets[project.project_name] = bullets
        result.llm_enhanced = True

    # Generate portfolio summary
    portfolio_prompt = build_portfolio_prompt(portfolio)
    portfolio_response = _query_llm(portfolio_prompt, model)

    if not portfolio_response:
        raise RuntimeError("LLM failed to generate portfolio summary")

    # Parse summary and skills from response
    if "SUMMARY:" in portfolio_response:
        parts = portfolio_response.split("SKILLS:")
        summary_part = parts[0].replace("SUMMARY:", "").strip()
        result.professional_summary = summary_part
        if len(parts) > 1:
            result.skills_section = parts[1].strip()
    else:
        # Response didn't follow format, use as summary
        result.professional_summary = portfolio_response[:500]

    result.model_used = model

    # Populate new sections from portfolio facts (set by analysis pipeline)
    result.skill_evolution = portfolio.skill_evolution_narrative
    result.developer_profile = portfolio.developer_fingerprint
    result.complexity_highlights = portfolio.complexity_narrative
    result.work_breakdown = portfolio.total_commit_breakdown or None

    return result


def generate_without_llm(portfolio: PortfolioFacts) -> ResumeContent:
    """
    Generate resume content using only templates (no LLM).

    This is the fallback that works on any machine without Ollama.
    """
    result = ResumeContent(
        project_bullets={},
        llm_enhanced=False,
    )

    for project in portfolio.projects:
        result.project_bullets[project.project_name] = generate_template_bullets(project)

    result.professional_summary = generate_template_summary(portfolio)
    result.skills_section = generate_template_skills(portfolio)

    return result
