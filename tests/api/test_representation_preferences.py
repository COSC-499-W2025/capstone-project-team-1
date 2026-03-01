"""Tests for the `RepresentationPreferences` Pydantic model."""

from datetime import date

import pytest
from pydantic import ValidationError

from artifactminer.api.schemas import RepresentationPreferences


def test_defaults_are_empty_lists():
    rp = RepresentationPreferences()
    assert rp.showcase_project_ids == []
    assert rp.project_order == []
    assert rp.skills_to_highlight == []
    assert rp.hidden_skills == []
    assert rp.chronology_overrides == []
    assert rp.comparison_attributes == []
    assert rp.custom_rankings == []


def test_accepts_valid_payload_and_parses_dates():
    payload = {
        "showcase_project_ids": [1, 2],
        "project_order": [2, 1],
        "skills_to_highlight": [10, 11],
        "hidden_skills": [12],
        "chronology_overrides": [
            {"project_id": 1, "first_commit": "2020-01-01", "last_commit": "2020-12-31"}
        ],
        "comparison_attributes": ["languages", "skills"],
        "custom_rankings": [{"project_id": 1, "rank": 1}, {"project_id": 2, "rank": 2}],
    }

    rp = RepresentationPreferences(**payload)

    assert rp.showcase_project_ids == [1, 2]
    assert rp.project_order == [2, 1]
    assert rp.skills_to_highlight == [10, 11]
    assert rp.hidden_skills == [12]
    assert isinstance(rp.chronology_overrides[0].first_commit, date)
    assert rp.chronology_overrides[0].first_commit == date(2020, 1, 1)
    assert rp.chronology_overrides[0].last_commit == date(2020, 12, 31)
    assert rp.comparison_attributes == ["languages", "skills"]
    assert rp.custom_rankings[0].project_id == 1
    assert rp.custom_rankings[0].rank == 1


def test_invalid_comparison_attribute_raises():
    payload = {"comparison_attributes": ["not_an_attribute"]}
    with pytest.raises(ValidationError):
        RepresentationPreferences(**payload)


def test_custom_ranking_rank_must_be_ge_1():
    payload = {"custom_rankings": [{"project_id": 1, "rank": 0}]}
    with pytest.raises(ValidationError):
        RepresentationPreferences(**payload)
