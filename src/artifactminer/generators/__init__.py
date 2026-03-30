"""Shared HTML artifact generation helpers and contracts."""

from __future__ import annotations

from .models import ExpertiseLevel, aggregate_skill_proficiency, proficiency_to_level


def generate_resume_html(*args, **kwargs):
    """Lazy proxy so issue #510 can expose the shared surface before landing."""
    from .resume_html import generate_resume_html as implementation

    path = implementation(*args, **kwargs)
    generate_resume_html.last_warnings = list(
        getattr(implementation, "last_warnings", [])
    )
    return path


def generate_portfolio_html(*args, **kwargs):
    """Lazy proxy so issue #511 can share the same package surface."""
    from .portfolio_html import generate_portfolio_html as implementation

    path = implementation(*args, **kwargs)
    generate_portfolio_html.last_warnings = list(
        getattr(implementation, "last_warnings", [])
    )
    return path


__all__ = [
    "ExpertiseLevel",
    "aggregate_skill_proficiency",
    "generate_portfolio_html",
    "generate_resume_html",
    "proficiency_to_level",
]

generate_resume_html.last_warnings = []
generate_portfolio_html.last_warnings = []
