"""
Resume generation module - Static-First, LLM-Light architecture.

This module generates resume content from git repositories using:
1. Static analysis (skills, insights, metrics) - does 90% of the work
2. Optional LLM enhancement - just polishes the prose

Usage:
    from artifactminer.resume import generate_resume

    result = generate_resume(
        zip_path="/path/to/repos.zip",
        user_email="user@example.com",
        use_llm=True,  # Set False to skip LLM
    )

    print(result.to_markdown())
"""

from .generate import generate_resume, GenerationResult
from .facts import ProjectFacts, PortfolioFacts
from .enhance import ResumeContent

__all__ = [
    "generate_resume",
    "GenerationResult",
    "ProjectFacts",
    "PortfolioFacts",
    "ResumeContent",
]
