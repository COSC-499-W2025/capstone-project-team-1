from datetime import date, datetime

from artifactminer.evidence.extractors.insight_bridge import insights_to_evidence
from artifactminer.skills.deep_analysis import Insight


def test_insights_to_evidence_maps_content_source_and_date():
    insights = [
        Insight(
            title="API design and architecture",
            evidence=["validation used", "dependency injection"],
            why_it_matters="Shows mature service boundaries.",
        )
    ]

    out = insights_to_evidence(insights, repo_last_commit=datetime(2025, 5, 1, 10, 0, 0))

    assert len(out) == 1
    assert out[0].type == "evaluation"
    assert out[0].content == "API design and architecture: Shows mature service boundaries."
    assert out[0].source == "validation used; dependency injection"
    assert out[0].date == date(2025, 5, 1)


def test_insights_to_evidence_uses_none_source_when_evidence_empty():
    out = insights_to_evidence(
        [Insight(title="Complexity awareness", evidence=[], why_it_matters="Controls cost.")],
        repo_last_commit=date(2025, 1, 2),
    )

    assert len(out) == 1
    assert out[0].source is None
    assert out[0].date == date(2025, 1, 2)


def test_insights_to_evidence_skips_empty_records():
    out = insights_to_evidence(
        [
            Insight(title="", evidence=["x"], why_it_matters=""),
            Insight(title=" ", evidence=["x"], why_it_matters=" "),
            Insight(title="Valid", evidence=["x"], why_it_matters="ok"),
        ]
    )

    assert len(out) == 1
    assert out[0].content == "Valid: ok"


def test_insights_to_evidence_limits_source_to_first_five_items():
    out = insights_to_evidence(
        [
            Insight(
                title="Robustness",
                evidence=["e1", "e2", "e3", "e4", "e5", "e6"],
                why_it_matters="Resilience",
            )
        ]
    )

    assert out[0].source == "e1; e2; e3; e4; e5"
