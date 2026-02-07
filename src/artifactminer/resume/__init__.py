"""
Resume generation module.

Two pipelines available:
  - v2 (generate_resume): Static-First, LLM-Light — original pipeline
  - v3 (generate_resume_v3): EXTRACT → QUERY → ASSEMBLE — richer data extraction

Usage (v3 — recommended):
    from artifactminer.resume import generate_resume_v3
    from artifactminer.resume.assembler import assemble_markdown

    result = generate_resume_v3(
        zip_path="/path/to/repos.zip",
        user_email="user@example.com",
    )
    print(assemble_markdown(result))
"""

# v3 pipeline (new)
from .pipeline import generate_resume_v3
from .models import ProjectDataBundle, PortfolioDataBundle, ResumeOutput
from .assembler import assemble_markdown, assemble_json

# v2 pipeline (kept for rollback)
from .generate import generate_resume, GenerationResult
from .facts import ProjectFacts, PortfolioFacts
from .enhance import ResumeContent

__all__ = [
    # v3
    "generate_resume_v3",
    "ProjectDataBundle",
    "PortfolioDataBundle",
    "ResumeOutput",
    "assemble_markdown",
    "assemble_json",
    # v2 (legacy)
    "generate_resume",
    "GenerationResult",
    "ProjectFacts",
    "PortfolioFacts",
    "ResumeContent",
]
