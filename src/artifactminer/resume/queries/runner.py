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
    RawProjectFacts,
    ResumeOutput,
    UserFeedback,
)
from .prompts import (
    PROJECT_SYSTEM,
    SUMMARY_SYSTEM,
    EXTRACTION_SYSTEM,
    DRAFT_SYSTEM,
    POLISH_SYSTEM,
    build_project_prompt,
    build_summary_prompt,
    build_skills_prompt,
    build_profile_prompt,
    build_extraction_prompt,
    build_draft_prompt,
    build_polish_prompt,
)

log = logging.getLogger(__name__)


_SECTION_HEADER_LINE_RE = re.compile(
    r"^\s*(?:[#>\-]+\s*)?(?:\*\*)?\s*"
    r"(DESCRIPTION|BULLETS|NARRATIVE)\s*"
    r"(?:\*\*)?\s*:\s*(?:\*\*)?\s*(.*)$",
    re.I,
)

_BULLET_LINE_RE = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+(.+)$")

_SKILLS_HEADER_RE = re.compile(
    r"^\s*(?:[-*•]\s*)?"
    r"(Languages|Frameworks\s*&\s*Libraries|Frameworks|"
    r"Tools\s*&\s*Infrastructure|Infrastructure|Practices)"
    r"\s*:\s*(.*)$",
    re.I,
)

_COMMON_LANGUAGES = {
    "python",
    "javascript",
    "typescript",
    "java",
    "go",
    "rust",
    "c",
    "c++",
    "c#",
    "kotlin",
    "swift",
    "php",
    "ruby",
    "scala",
    "r",
    "dart",
    "tf",
}

_TOOL_KEYWORDS = {
    "terraform",
    "docker",
    "kubernetes",
    "helm",
    "aws",
    "gcp",
    "azure",
    "ansible",
    "jenkins",
    "github actions",
    "gitlab ci",
    "linux",
    "bash",
    "shell",
    "prometheus",
    "grafana",
    "nginx",
    "vpc",
    "s3",
    "ec2",
    "lambda",
    "cloudformation",
    "ci/cd",
    "ci cd",
}


def _query(
    prompt: str,
    model: str,
    system: str,
    *,
    temperature: float | None = None,
    max_tokens: int = 1024,
    top_p: float | None = None,
    repetition_penalty: float | None = None,
) -> str:
    """Execute a single LLM query with per-model sampling defaults."""
    from ..llm_client import get_sampling_params, query_llm_text

    # Merge per-model defaults with explicit overrides
    sampling = get_sampling_params(model)
    effective_temp = temperature if temperature is not None else sampling.get("temperature", 0.2)
    effective_top_p = top_p if top_p is not None else sampling.get("top_p")
    effective_rep_pen = (
        repetition_penalty
        if repetition_penalty is not None
        else sampling.get("repetition_penalty")
    )

    return query_llm_text(
        prompt=prompt,
        model=model,
        system=system,
        temperature=effective_temp,
        max_tokens=max_tokens,
        top_p=effective_top_p,
        repetition_penalty=effective_rep_pen,
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

    if not text or not text.strip():
        return section

    raw_lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    parsed_sections = {"description": [], "bullets": [], "narrative": []}

    current_key: str | None = None
    found_structured_markers = False
    for raw_line in raw_lines:
        line = raw_line.rstrip()
        marker = _SECTION_HEADER_LINE_RE.match(line)
        if marker:
            found_structured_markers = True
            current_key = marker.group(1).lower()
            tail = marker.group(2).strip()
            if tail:
                parsed_sections[current_key].append(tail)
            continue
        if current_key:
            parsed_sections[current_key].append(line)

    if found_structured_markers:
        section.description = _clean_text_block(
            parsed_sections["description"],
            drop_bullets=True,
        )
        section.bullets = _extract_bullets(parsed_sections["bullets"])
        section.narrative = _clean_text_block(
            parsed_sections["narrative"],
            drop_bullets=True,
        )

    # Fallback: extract bullets from the whole response
    if not section.bullets:
        section.bullets = _extract_bullets(raw_lines)

    # Fallback: derive description from non-bullet lines
    if not section.description:
        non_bullet_lines = [
            line
            for line in raw_lines
            if not _BULLET_LINE_RE.match(line.strip())
            and not _SECTION_HEADER_LINE_RE.match(line.strip())
        ]
        section.description = _clean_text_block(non_bullet_lines, drop_bullets=True)

    # Last resort: use a trimmed version of the response
    if not section.bullets and not section.description:
        section.description = _clean_text_block([text])[:500]

    return section


def _clean_text_block(lines: list[str], *, drop_bullets: bool = False) -> str:
    """Normalize a generated text block by stripping markdown noise."""
    cleaned: list[str] = []

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            if cleaned and cleaned[-1] != "":
                cleaned.append("")
            continue

        line = re.sub(r"^>\s*", "", line)

        if _SECTION_HEADER_LINE_RE.match(line):
            continue
        if drop_bullets and _BULLET_LINE_RE.match(line):
            continue
        if re.fullmatch(r"[\s*_`#>\-]+", line):
            continue

        line = _clean_inline_text(line)
        if line:
            cleaned.append(line)

    text = "\n".join(cleaned).strip()
    return re.sub(r"\n{3,}", "\n\n", text)


def _clean_inline_text(text: str) -> str:
    """Normalize markdown-heavy inline text to plain resume prose."""
    value = text.strip()
    value = value.replace("**", "")
    value = value.replace("__", "")
    value = value.replace("`", "")
    value = re.sub(r"\s+", " ", value).strip()
    value = re.sub(r"\s+([,.;:!?])", r"\1", value)
    return value.strip(" -*")


def _extract_bullets(lines: list[str]) -> list[str]:
    """Extract and deduplicate bullet lines from model output."""
    bullets: list[str] = []
    seen: set[str] = set()

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        match = _BULLET_LINE_RE.match(line)
        if not match:
            continue

        bullet = _clean_inline_text(match.group(1))
        if not bullet:
            continue
        if _SECTION_HEADER_LINE_RE.match(bullet):
            continue
        if re.match(r"^(DESCRIPTION|BULLETS|NARRATIVE)\s*:", bullet, re.I):
            continue

        key = bullet.casefold()
        if key in seen:
            continue
        seen.add(key)
        bullets.append(bullet)

    return bullets


def _clean_summary_or_profile(text: str) -> str:
    """Strip optional section labels from summary/profile responses."""
    cleaned = _clean_text_block(text.splitlines())
    cleaned = re.sub(
        r"^(SUMMARY|PROFILE|DEVELOPER PROFILE)\s*:\s*", "", cleaned, flags=re.I
    )
    return cleaned.strip()


def _normalize_skills_section(raw: str, portfolio: PortfolioDataBundle) -> str:
    """Parse, clean, and normalize the skills section into stable categories."""
    categories: dict[str, list[str]] = {
        "languages": [],
        "frameworks": [],
        "tools": [],
        "practices": [],
    }

    current_category: str | None = None
    for raw_line in raw.splitlines():
        line = raw_line.strip()
        if not line:
            current_category = None
            continue

        header = _SKILLS_HEADER_RE.match(line)
        if header:
            current_category = _normalize_category_name(header.group(1))
            categories[current_category].extend(_split_skills(header.group(2)))
            continue

        if current_category and (line.startswith(("-", "*", "•")) or "," in line):
            categories[current_category].extend(_split_skills(line))

    # Fill gaps with deterministic portfolio data
    if not categories["languages"]:
        categories["languages"].extend(portfolio.languages_used[:8])
    if not categories["frameworks"]:
        categories["frameworks"].extend(portfolio.frameworks_used[:10])
    if not categories["practices"]:
        categories["practices"].extend(portfolio.top_skills[:15])

    if not categories["tools"]:
        tool_candidates = portfolio.frameworks_used + portfolio.top_skills
        categories["tools"].extend(
            item for item in tool_candidates if _looks_like_tool(item)
        )

    language_tokens = {
        _normalize_token(name)
        for name in (_COMMON_LANGUAGES | set(portfolio.languages_used))
    }

    # Ensure languages are only listed under Languages
    for cat in ("frameworks", "tools", "practices"):
        keep: list[str] = []
        for item in categories[cat]:
            cleaned = _clean_inline_text(item)
            if not cleaned:
                continue
            if _normalize_token(cleaned) in language_tokens:
                categories["languages"].append(cleaned)
            else:
                keep.append(cleaned)
        categories[cat] = keep

    ordered = ["languages", "frameworks", "tools", "practices"]
    deduped: dict[str, list[str]] = {k: [] for k in ordered}
    seen_global: set[str] = set()

    for cat in ordered:
        for item in categories[cat]:
            cleaned = _clean_inline_text(item)
            if not cleaned:
                continue
            key = cleaned.casefold()
            if key in seen_global:
                continue
            seen_global.add(key)
            deduped[cat].append(cleaned)

    lines: list[str] = []
    if deduped["languages"]:
        lines.append(f"Languages: {', '.join(deduped['languages'])}")
    if deduped["frameworks"]:
        lines.append(f"Frameworks & Libraries: {', '.join(deduped['frameworks'])}")
    if deduped["tools"]:
        lines.append(f"Tools & Infrastructure: {', '.join(deduped['tools'])}")
    if deduped["practices"]:
        lines.append(f"Practices: {', '.join(deduped['practices'])}")

    if lines:
        return "\n".join(lines)

    # Last-resort fallback
    return _clean_text_block(raw.splitlines())


def _normalize_category_name(raw: str) -> str:
    """Map category headers to canonical keys."""
    key = raw.strip().casefold()
    if "language" in key:
        return "languages"
    if "framework" in key:
        return "frameworks"
    if "tool" in key or "infrastructure" in key:
        return "tools"
    return "practices"


def _split_skills(raw: str) -> list[str]:
    """Split a skills line into individual items."""
    text = _clean_inline_text(raw)
    if not text:
        return []

    text = re.sub(r"^[-*•]\s*", "", text)
    parts = [segment.strip() for segment in re.split(r"[,;|]", text)]
    items: list[str] = []
    for part in parts:
        cleaned = _clean_inline_text(part)
        if cleaned:
            items.append(cleaned)
    return items


def _normalize_token(text: str) -> str:
    """Normalize an item for case-insensitive matching."""
    return re.sub(r"[^a-z0-9#+]+", "", text.casefold())


def _looks_like_tool(item: str) -> bool:
    """Heuristic for infra/tooling skill names."""
    lowered = item.casefold()
    return any(keyword in lowered for keyword in _TOOL_KEYWORDS)


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
    response = _query(
        prompt,
        model,
        PROJECT_SYSTEM,
        max_tokens=768,
    )

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
    summary = _clean_summary_or_profile(
        _query(
            summary_prompt,
            model,
            SUMMARY_SYSTEM,
            max_tokens=256,
        )
    )

    # 2. Skills section
    if progress:
        progress("Generating skills section...")
    skills_prompt = build_skills_prompt(portfolio)
    raw_skills = _query(
        skills_prompt,
        model,
        SUMMARY_SYSTEM,
        max_tokens=320,
    )
    skills = _normalize_skills_section(raw_skills, portfolio)

    # 3. Developer profile
    if progress:
        progress("Generating developer profile...")
    profile_prompt = build_profile_prompt(portfolio)
    profile = _clean_summary_or_profile(
        _query(
            profile_prompt,
            model,
            SUMMARY_SYSTEM,
            max_tokens=320,
        )
    )

    return summary, skills, profile


# ---------------------------------------------------------------------------
# Multi-stage pipeline queries (Strategy B)
# ---------------------------------------------------------------------------

_FACTS_SECTION_RE = re.compile(
    r"^\s*(?:[-*•]|\d+[.)])\s+(.+)$",
)

_EXTRACTION_HEADER_RE = re.compile(
    r"^\s*(PROJECT_SUMMARY|FACTS|ROLE)\s*:\s*(.*)$",
    re.I,
)


def _parse_extraction_response(text: str, project_name: str) -> RawProjectFacts:
    """Parse the structured PROJECT_SUMMARY/FACTS/ROLE response from Stage 1."""
    facts = RawProjectFacts(project_name=project_name)

    if not text or not text.strip():
        return facts

    current_section: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        header = _EXTRACTION_HEADER_RE.match(line)
        if header:
            current_section = header.group(1).upper()
            tail = header.group(2).strip()
            if current_section == "PROJECT_SUMMARY" and tail:
                facts.summary = _clean_inline_text(tail)
            elif current_section == "ROLE" and tail:
                facts.role = _clean_inline_text(tail)
            continue

        if current_section == "FACTS":
            bullet = _FACTS_SECTION_RE.match(line)
            if bullet:
                cleaned = _clean_inline_text(bullet.group(1))
                if cleaned:
                    facts.facts.append(cleaned)
        elif current_section == "PROJECT_SUMMARY" and not facts.summary:
            facts.summary = _clean_inline_text(line)
        elif current_section == "ROLE" and not facts.role:
            facts.role = _clean_inline_text(line)

    return facts


def _parse_draft_response(text: str) -> ResumeOutput:
    """Parse the complete draft resume from Stage 2 into a ResumeOutput."""
    output = ResumeOutput(stage="draft")

    if not text or not text.strip():
        return output

    current_section: str | None = None
    current_project: str | None = None
    project_lines: dict[str, dict[str, list[str]]] = {}

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        # Check for top-level markers
        if line.upper().startswith("PROFESSIONAL_SUMMARY:"):
            current_section = "summary"
            tail = line.split(":", 1)[1].strip()
            if tail:
                output.professional_summary = _clean_inline_text(tail)
            continue

        if line.upper().startswith("DEVELOPER_PROFILE:"):
            current_section = "profile"
            tail = line.split(":", 1)[1].strip()
            if tail:
                output.developer_profile = _clean_inline_text(tail)
            continue

        if line.upper().startswith("SKILLS:"):
            current_section = "skills"
            tail = line.split(":", 1)[1].strip()
            if tail:
                output.skills_section = tail
            continue

        if line.upper().startswith("PROJECT:"):
            current_section = "project"
            current_project = line.split(":", 1)[1].strip()
            project_lines[current_project] = {
                "description": [],
                "bullets": [],
                "narrative": [],
            }
            continue

        # Parse project sub-sections (check for markers in any project_* state)
        if current_project and (
            current_section == "project"
            or (current_section and current_section.startswith("project_"))
        ):
            marker = _SECTION_HEADER_LINE_RE.match(line)
            if marker:
                key = marker.group(1).lower()
                tail = marker.group(2).strip()
                if tail and key in project_lines[current_project]:
                    project_lines[current_project][key].append(tail)
                current_section = f"project_{key}"
                continue

        if current_section == "project_description" and current_project:
            project_lines[current_project]["description"].append(line)
        elif current_section == "project_bullets" and current_project:
            bullet = _BULLET_LINE_RE.match(line)
            if bullet:
                project_lines[current_project]["bullets"].append(
                    _clean_inline_text(bullet.group(1))
                )
        elif current_section == "project_narrative" and current_project:
            project_lines[current_project]["narrative"].append(line)
        elif current_section == "summary" and not output.professional_summary:
            output.professional_summary = _clean_inline_text(line)
        elif current_section == "profile" and not output.developer_profile:
            output.developer_profile = _clean_inline_text(line)
        elif current_section == "skills":
            output.skills_section += "\n" + line

    # Build project sections
    for name, parts in project_lines.items():
        section = ProjectSection(
            description=_clean_inline_text(" ".join(parts["description"])),
            bullets=[b for b in parts["bullets"] if b],
            narrative=_clean_inline_text(" ".join(parts["narrative"])),
        )
        output.project_sections[name] = section

    if output.skills_section:
        output.skills_section = output.skills_section.strip()

    return output


def run_extraction_query(
    bundle: ProjectDataBundle,
    model: str,
    *,
    progress: Optional[Callable[[str], None]] = None,
) -> RawProjectFacts:
    """
    Stage 1: Extract structured facts from a project using LFM2.5-1.2B.

    Returns RawProjectFacts with summary, facts list, and role.
    """
    if progress:
        progress(f"  [Stage 1] Extracting facts for {bundle.project_name}...")

    prompt = build_extraction_prompt(bundle)
    response = _query(
        prompt,
        model,
        EXTRACTION_SYSTEM,
        max_tokens=512,
    )

    if not response.strip():
        raise RuntimeError(
            f"LLM returned empty response for extraction of {bundle.project_name}"
        )

    return _parse_extraction_response(response, bundle.project_name)


def run_draft_queries(
    raw_facts: dict[str, RawProjectFacts],
    portfolio: PortfolioDataBundle,
    model: str,
    *,
    progress: Optional[Callable[[str], None]] = None,
) -> ResumeOutput:
    """
    Stage 2: Generate a first-draft resume from extracted facts using Qwen3-1.7B.

    Returns a complete ResumeOutput with stage="draft".
    """
    if progress:
        progress("[Stage 2] Generating draft resume...")

    prompt = build_draft_prompt(raw_facts, portfolio)
    response = _query(
        prompt,
        model,
        DRAFT_SYSTEM,
        max_tokens=2048,
    )

    if not response.strip():
        raise RuntimeError("LLM returned empty response for draft generation")

    output = _parse_draft_response(response)
    output.portfolio_data = portfolio
    output.raw_project_facts = raw_facts

    # Fallback: if parsing didn't find project sections, try single-project parsing
    if not output.project_sections:
        section = _parse_project_response(response)
        if section.description or section.bullets:
            for name in raw_facts:
                output.project_sections[name] = section
                break

    # Normalize skills section
    if output.skills_section and portfolio:
        output.skills_section = _normalize_skills_section(
            output.skills_section, portfolio
        )

    return output


def run_polish_query(
    draft_output: ResumeOutput,
    feedback: UserFeedback,
    model: str,
    *,
    progress: Optional[Callable[[str], None]] = None,
) -> ResumeOutput:
    """
    Stage 3: Polish the draft resume with user feedback using Qwen3-4B.

    Returns the final polished ResumeOutput with stage="polish".
    """
    if progress:
        progress("[Stage 3] Polishing resume with feedback...")

    prompt = build_polish_prompt(draft_output, feedback)
    response = _query(
        prompt,
        model,
        POLISH_SYSTEM,
        max_tokens=2048,
    )

    if not response.strip():
        # Fall back to the draft if polish fails
        log.warning("Polish stage returned empty response, using draft")
        draft_output.stage = "polish"
        return draft_output

    output = _parse_draft_response(response)
    output.stage = "polish"
    output.portfolio_data = draft_output.portfolio_data
    output.raw_project_facts = draft_output.raw_project_facts

    # Preserve draft sections if polish didn't produce them
    if not output.professional_summary and draft_output.professional_summary:
        output.professional_summary = draft_output.professional_summary
    if not output.skills_section and draft_output.skills_section:
        output.skills_section = draft_output.skills_section
    if not output.developer_profile and draft_output.developer_profile:
        output.developer_profile = draft_output.developer_profile
    if not output.project_sections and draft_output.project_sections:
        output.project_sections = dict(draft_output.project_sections)

    # Normalize skills
    if output.skills_section and output.portfolio_data:
        output.skills_section = _normalize_skills_section(
            output.skills_section, output.portfolio_data
        )

    return output
