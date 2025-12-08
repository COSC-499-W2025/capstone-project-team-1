"""Demo package - Requirements compliance showcase for Artifact Miner."""

from demo.requirements import (
    REQUIREMENTS,
    Requirement,
    demonstrated_requirements,
    get_requirement,
    get_requirements_by_section,
)
from demo.theme import BANNER_ART, TEAM_INFO, NAV_HINTS, STATUS_ICONS
from demo.components import (
    console,
    truncate,
    format_timestamp,
    animate_spinner,
    section_header,
    print_splash_screen,
    print_requirement_banner,
    print_how_banner,
    show_final_scorecard,
)

__all__ = [
    # Requirements
    "REQUIREMENTS",
    "Requirement",
    "demonstrated_requirements",
    "get_requirement",
    "get_requirements_by_section",
    # Theme
    "BANNER_ART",
    "TEAM_INFO",
    "NAV_HINTS",
    "STATUS_ICONS",
    # Components
    "console",
    "truncate",
    "format_timestamp",
    "animate_spinner",
    "section_header",
    "print_splash_screen",
    "print_requirement_banner",
    "print_how_banner",
    "show_final_scorecard",
]
