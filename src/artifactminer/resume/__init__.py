"""
Resume generation module.

Usage:
    from artifactminer.resume import generate_resume_v3_multistage
    from artifactminer.resume.assembler import assemble_markdown

    result = generate_resume_v3_multistage(
        zip_path="/path/to/repos.zip",
        user_email="user@example.com",
    )
    print(assemble_markdown(result))
"""

from .pipeline import generate_resume_v3_multistage, extract_and_distill
from .models import ProjectDataBundle, PortfolioDataBundle, ResumeOutput
from .assembler import assemble_markdown, assemble_json

# v2 pipeline (kept for rollback)
from .generate import generate_resume, GenerationResult
from .facts import ProjectFacts, PortfolioFacts
from .enhance import ResumeContent

__all__ = [
    # v3 multi-stage pipeline
    "generate_resume_v3_multistage",
    "extract_and_distill",
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
