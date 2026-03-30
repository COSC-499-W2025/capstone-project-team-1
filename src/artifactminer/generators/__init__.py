"""Shared HTML artifact generation helpers and contracts."""

from __future__ import annotations

from .models import ExpertiseLevel, aggregate_skill_proficiency, proficiency_to_level


def generate_portfolio_html(*args, **kwargs):
    """Lazy proxy so the foundation can expose the shared surface before #511 lands."""
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
    "proficiency_to_level",
]

generate_portfolio_html.last_warnings = []
