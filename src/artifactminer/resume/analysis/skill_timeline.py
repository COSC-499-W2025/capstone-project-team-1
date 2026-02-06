"""
Skill Evolution Timeline.

Determines when each skill was first demonstrated in the git history,
then uses a single LLM call to generate a temporal growth narrative.

This produces output like:
"Adopted TypeScript in March 2024, added testing in June, moved to async patterns by September"

90% static analysis (skill dates from git), 10% LLM (narrative generation).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from git import Repo
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class SkillAppearance:
    """Records when a skill was first demonstrated."""
    skill_name: str
    first_date: str  # ISO format
    project_name: str
    evidence: str  # e.g., "FastAPI import in api/main.py"


class SkillTimelineNarrative(BaseModel):
    narrative: str
    milestones: list[str]


# ---------------------------------------------------------------------------
# Static analysis: find skill first-appearances
# ---------------------------------------------------------------------------

# Map skill names to file patterns that indicate their use
SKILL_FILE_PATTERNS: Dict[str, List[str]] = {
    "Python": [".py"],
    "JavaScript": [".js", ".jsx"],
    "TypeScript": [".ts", ".tsx"],
    "Java": [".java"],
    "Go": [".go"],
    "Rust": [".rs"],
    "C++": [".cpp", ".hpp", ".cc"],
    "React": [".jsx", ".tsx"],
    "FastAPI": ["fastapi"],
    "SQLAlchemy": ["sqlalchemy"],
    "pytest": ["test_", "_test.py", "conftest.py"],
    "Testing": ["test_", "_test.py", "spec.", ".test."],
    "Docker": ["Dockerfile", "docker-compose"],
    "CI/CD": [".github/workflows", ".gitlab-ci", "Jenkinsfile"],
    "REST API Design": ["router", "endpoint", "routes"],
    "Asynchronous Programming": ["async def", "await"],
    "Data Validation": ["pydantic", "validator", "schema"],
}


def compute_skill_first_appearances(
    repo_path: str,
    user_email: str,
    detected_skills: List[str],
    max_commits: int = 500,
) -> List[SkillAppearance]:
    """
    For each detected skill, find the earliest commit where it appeared.

    Walks commits in reverse chronological order and checks which files
    match skill patterns.

    Args:
        repo_path: Path to the git repository
        user_email: Author email to filter by
        detected_skills: List of skill names from the skill extractor
        max_commits: Maximum commits to scan

    Returns:
        List of SkillAppearance sorted by first_date (earliest first)
    """
    repo = Repo(repo_path)
    project_name = repo.working_dir.split("/")[-1] if repo.working_dir else "unknown"

    # Build a lookup: skill → file patterns to match
    skills_to_find = set(detected_skills)
    skill_patterns: Dict[str, List[str]] = {}
    for skill in skills_to_find:
        if skill in SKILL_FILE_PATTERNS:
            skill_patterns[skill] = SKILL_FILE_PATTERNS[skill]
        else:
            # Generic: look for the skill name in file paths (lowercase)
            skill_patterns[skill] = [skill.lower().replace(" ", "_")]

    # Track earliest date per skill
    skill_earliest: Dict[str, tuple[str, str]] = {}  # skill → (date, evidence)

    count = 0
    for commit in repo.iter_commits():
        if count >= max_commits:
            break
        if not (commit.author.email and commit.author.email.lower() == user_email.lower()):
            continue
        count += 1

        commit_date = commit.committed_datetime.isoformat()
        changed_files = list(commit.stats.files.keys())

        for skill, patterns in skill_patterns.items():
            for filepath in changed_files:
                fp_lower = filepath.lower()
                if any(p.lower() in fp_lower for p in patterns):
                    # This commit touches a file related to this skill
                    if skill not in skill_earliest or commit_date < skill_earliest[skill][0]:
                        skill_earliest[skill] = (commit_date, filepath)
                    break

    # Build sorted list
    appearances = []
    for skill, (date, evidence) in skill_earliest.items():
        appearances.append(SkillAppearance(
            skill_name=skill,
            first_date=date,
            project_name=project_name,
            evidence=evidence,
        ))

    appearances.sort(key=lambda a: a.first_date)
    return appearances


# ---------------------------------------------------------------------------
# LLM narrative generation
# ---------------------------------------------------------------------------

TIMELINE_SYSTEM = (
    "You are a professional resume writer. Generate a concise 2-3 sentence "
    "narrative describing a developer's skill evolution over time. "
    "Focus on growth trajectory and technology adoption. "
    "Be specific with dates (use month names, not numbers)."
)


def generate_skill_timeline_narrative(
    appearances: List[SkillAppearance],
    model: str,
) -> Optional[SkillTimelineNarrative]:
    """
    Generate a narrative from skill first-appearance data.

    Args:
        appearances: Chronologically sorted skill appearances
        model: LLM model name

    Returns:
        SkillTimelineNarrative with narrative text and milestones,
        or None if there aren't enough data points.
    """
    from ..llm_client import query_llm

    if len(appearances) < 2:
        return None

    # Build pre-digested input for the LLM
    lines = []
    for a in appearances:
        try:
            dt = datetime.fromisoformat(a.first_date)
            date_str = dt.strftime("%B %Y")  # e.g., "March 2024"
        except (ValueError, TypeError):
            date_str = a.first_date[:10]

        lines.append(f"- {date_str}: {a.skill_name} (in {a.project_name})")

    prompt = (
        "Generate a 2-3 sentence skill evolution narrative from this chronological data:\n\n"
        + "\n".join(lines)
        + "\n\nWrite a concise narrative showing technical growth over time."
        + " Also list 2-4 key milestones."
    )

    return query_llm(
        prompt,
        SkillTimelineNarrative,
        model=model,
        system=TIMELINE_SYSTEM,
        temperature=0.3,
    )
