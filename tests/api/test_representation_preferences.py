"""Tests for the `RepresentationPreferences` Pydantic model."""

from datetime import date

import pytest
from pydantic import ValidationError

from artifactminer.api.schemas import (
    RepresentationPreferences,
    ChronologyOverride,
    CustomRanking,
)


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


def test_chronology_override_requires_project_id():
    payload = {"chronology_overrides": [{"first_commit": "2020-01-01"}]}
    with pytest.raises(ValidationError):
        RepresentationPreferences(**payload)


def test_chronology_override_partial_dates():
    payload = {
        "chronology_overrides": [
            {"project_id": 5, "first_commit": "2021-06-15"},
            {"project_id": 6, "last_commit": "2023-12-31"}
        ]
    }
    rp = RepresentationPreferences(**payload)
    assert rp.chronology_overrides[0].first_commit == date(2021, 6, 15)
    assert rp.chronology_overrides[0].last_commit is None
    assert rp.chronology_overrides[1].first_commit is None
    assert rp.chronology_overrides[1].last_commit == date(2023, 12, 31)


def test_custom_ranking_requires_project_id():
    payload = {"custom_rankings": [{"rank": 1}]}
    with pytest.raises(ValidationError):
        RepresentationPreferences(**payload)


def test_custom_ranking_requires_rank():
    payload = {"custom_rankings": [{"project_id": 1}]}
    with pytest.raises(ValidationError):
        RepresentationPreferences(**payload)


class TestChronologyOverride:
    """Tests for the ChronologyOverride model."""

    def test_requires_project_id(self):
        with pytest.raises(ValidationError) as exc_info:
            ChronologyOverride()
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("project_id",) for e in errors)

    def test_valid_with_project_id_only(self):
        override = ChronologyOverride(project_id=1)
        assert override.project_id == 1
        assert override.first_commit is None
        assert override.last_commit is None

    def test_valid_with_both_dates(self):
        override = ChronologyOverride(
            project_id=3,
            first_commit=date(2020, 6, 15),
            last_commit=date(2023, 6, 15)
        )
        assert override.project_id == 3
        assert override.first_commit == date(2020, 6, 15)
        assert override.last_commit == date(2023, 6, 15)

    def test_parse_dates_as_strings(self):
        override = ChronologyOverride(
            project_id=7,
            first_commit="2021-03-20",
            last_commit="2022-09-10"
        )
        assert isinstance(override.first_commit, date)
        assert isinstance(override.last_commit, date)
        assert override.first_commit == date(2021, 3, 20)
        assert override.last_commit == date(2022, 9, 10)

    def test_invalid_date_format(self):
        with pytest.raises(ValidationError):
            ChronologyOverride(project_id=1, first_commit="01/01/2020")


class TestCustomRanking:
    """Tests for the CustomRanking model."""

    def test_requires_project_id(self):
        with pytest.raises(ValidationError) as exc_info:
            CustomRanking(rank=1)
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("project_id",) for e in errors)

    def test_requires_rank(self):
        with pytest.raises(ValidationError) as exc_info:
            CustomRanking(project_id=1)
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("rank",) for e in errors)

    def test_valid_with_project_id_and_rank(self):
        ranking = CustomRanking(project_id=1, rank=1)
        assert ranking.project_id == 1
        assert ranking.rank == 1

    def test_rank_minimum_value_is_one(self):
        with pytest.raises(ValidationError):
            CustomRanking(project_id=1, rank=0)

    def test_rank_negative_value_rejected(self):
        with pytest.raises(ValidationError):
            CustomRanking(project_id=1, rank=-1)
