"""Requirements database - All 20 project requirements with tracking."""

from dataclasses import dataclass
from typing import List


@dataclass
class Requirement:
    """A single project requirement with compliance info."""

    id: int
    short: str
    full: str
    status: str  # "FULLY MET", "PARTIALLY MET", "NOT MET"
    coverage: int  # 0-100
    how: str
    demo_sections: List[str]


# All 20 Requirements
REQUIREMENTS: List[Requirement] = [
    Requirement(
        id=1,
        short="User Consent",
        full="Require the user to give consent for data access before proceeding",
        status="FULLY MET",
        coverage=100,
        how="PUT /consent endpoint with 3-tier levels: full, no_llm, none. Consent checked before any data processing.",
        demo_sections=["consent"],
    ),
    Requirement(
        id=2,
        short="Parse Zipped Folders",
        full="Parse a specified zipped folder containing nested folders and files",
        status="FULLY MET",
        coverage=100,
        how="POST /zip/upload accepts ZIP, extracts via zipfile module, os.walk() traverses nested structure.",
        demo_sections=["zip_upload"],
    ),
    Requirement(
        id=3,
        short="Wrong Format Error",
        full="Return an error if the specified file is in the wrong format",
        status="FULLY MET",
        coverage=100,
        how="Upload validates file format, returns HTTP 422 'Only ZIP files are allowed.' for invalid formats.",
        demo_sections=["wrong_format"],
    ),
    Requirement(
        id=4,
        short="External Service Permission",
        full="Request user permission before using external services (e.g., LLM) and provide implications on data privacy",
        status="FULLY MET",
        coverage=100,
        how="Consent system gates LLM usage. Privacy implications shown before consent selection.",
        demo_sections=["consent"],
    ),
    Requirement(
        id=5,
        short="Alternative Analysis",
        full="Have alternative analyses in place if sending data to an external service is not permitted",
        status="FULLY MET",
        coverage=100,
        how="DeepRepoAnalyzer runs deterministic analysis. Template summaries generated when LLM disabled.",
        demo_sections=["analysis", "consent"],
    ),
    Requirement(
        id=6,
        short="Store User Config",
        full="Store user configurations for future use",
        status="FULLY MET",
        coverage=100,
        how="Question/UserAnswer tables persist responses. GET /questions + POST /answers endpoints.",
        demo_sections=["questionnaire"],
    ),
    Requirement(
        id=7,
        short="Individual vs Collaborative",
        full="Distinguish individual projects from collaborative projects",
        status="FULLY MET",
        coverage=100,
        how="RepoStats.is_collaborative detects remotes + multiple authors. Different skill tables per type.",
        demo_sections=["analysis"],
    ),
    Requirement(
        id=8,
        short="Identify Language & Framework",
        full="For a coding project, identify the programming language and framework used",
        status="FULLY MET",
        coverage=100,
        how="File extension analysis for languages. Framework detector scans manifests (requirements.txt, package.json, etc).",
        demo_sections=["analysis"],
    ),
    Requirement(
        id=9,
        short="Individual Contributions",
        full="Extrapolate individual contributions for a given collaboration project",
        status="FULLY MET",
        coverage=100,
        how="getUserRepoStats() filters commits by email. build_user_profile() extracts user-specific changes.",
        demo_sections=["analysis"],
    ),
    Requirement(
        id=10,
        short="Contribution Metrics",
        full="Extract key contribution metrics (duration, activity type frequency, etc)",
        status="FULLY MET",
        coverage=100,
        how="first_commit/last_commit timestamps, activity_classifier breaks down code/test/docs/config/design.",
        demo_sections=["analysis", "timeline"],
    ),
    Requirement(
        id=11,
        short="Extract Skills",
        full="Extract key skills from a given project",
        status="FULLY MET",
        coverage=100,
        how="Multi-signal extraction: language detection, dependency scanning, 20+ code regex patterns.",
        demo_sections=["analysis", "skills"],
    ),
    Requirement(
        id=12,
        short="Output Project Info",
        full="Output all the key information for a project",
        status="FULLY MET",
        coverage=100,
        how="POST /analyze returns comprehensive AnalyzeResponse with all project metadata.",
        demo_sections=["analysis"],
    ),
    Requirement(
        id=13,
        short="Store in Database",
        full="Store project information into a database",
        status="FULLY MET",
        coverage=100,
        how="SQLAlchemy models: RepoStat, UserRepoStat, ProjectSkill, ResumeItem, etc. SQLite persistence.",
        demo_sections=["analysis"],
    ),
    Requirement(
        id=14,
        short="Retrieve Portfolio",
        full="Retrieve previously generated portfolio information",
        status="FULLY MET",
        coverage=100,
        how="GET /summaries?user_email=X returns stored AI/template summaries.",
        demo_sections=["summaries"],
    ),
    Requirement(
        id=15,
        short="Retrieve Resume Items",
        full="Retrieve previously generated resume item",
        status="FULLY MET",
        coverage=100,
        how="GET /resume returns stored resume items with optional project_id filter.",
        demo_sections=["resume"],
    ),
    Requirement(
        id=16,
        short="Rank Projects",
        full="Rank importance of each project based on user's contributions",
        status="FULLY MET",
        coverage=100,
        how="rank_projects() calculates contribution %. Updates RepoStat.ranking_score.",
        demo_sections=["analysis", "ranking"],
    ),
    Requirement(
        id=17,
        short="Summarize Top Projects",
        full="Summarize the top ranked projects",
        status="FULLY MET",
        coverage=100,
        how="generate_summaries_for_ranked() creates GPT summaries (consent=full) or templates.",
        demo_sections=["summaries"],
    ),
    Requirement(
        id=18,
        short="Delete Insights Safely",
        full="Delete previously generated insights and ensure files shared across multiple reports do not get affected",
        status="FULLY MET",
        coverage=100,
        how="DELETE /projects/{id} performs soft delete (sets deleted_at). No disk files modified.",
        demo_sections=["delete"],
    ),
    Requirement(
        id=19,
        short="Chronological Projects",
        full="Produce a chronological list of projects",
        status="FULLY MET",
        coverage=100,
        how="GET /projects/timeline returns projects sorted by first_commit with duration calculation.",
        demo_sections=["timeline"],
    ),
    Requirement(
        id=20,
        short="Chronological Skills",
        full="Produce a chronological list of skills exercised",
        status="FULLY MET",
        coverage=100,
        how="GET /skills/chronology joins skills with projects, ordered by when first demonstrated.",
        demo_sections=["skills"],
    ),
]


def get_requirement(req_id: int) -> Requirement:
    """Get a requirement by ID."""
    for req in REQUIREMENTS:
        if req.id == req_id:
            return req
    raise ValueError(f"Requirement {req_id} not found")


def get_requirements_by_section(section: str) -> List[Requirement]:
    """Get all requirements for a demo section."""
    return [r for r in REQUIREMENTS if section in r.demo_sections]


# Track which requirements have been demonstrated
demonstrated_requirements: set[int] = set()
