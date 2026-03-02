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


def test_multiple_chronology_overrides_for_same_project():
    payload = {
        "chronology_overrides": [
            {"project_id": 1, "first_commit": "2020-01-01"},
            {"project_id": 1, "last_commit": "2021-12-31"}
        ]
    }
    rp = RepresentationPreferences(**payload)
    assert len(rp.chronology_overrides) == 2


def test_multiple_custom_rankings_for_same_project():
    payload = {
        "custom_rankings": [
            {"project_id": 1, "rank": 1},
            {"project_id": 1, "rank": 2}
        ]
    }
    rp = RepresentationPreferences(**payload)
    assert len(rp.custom_rankings) == 2


class TestChronologyOverride:
    """Tests for the ChronologyOverride model."""

    def test_requires_project_id(self):
        """ChronologyOverride must have a project_id."""
        with pytest.raises(ValidationError) as exc_info:
            ChronologyOverride()
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("project_id",) for e in errors)

    def test_valid_with_project_id_only(self):
        """ChronologyOverride is valid with only project_id."""
        override = ChronologyOverride(project_id=1)
        assert override.project_id == 1
        assert override.first_commit is None
        assert override.last_commit is None

    def test_valid_with_first_commit_only(self):
        """ChronologyOverride can have only first_commit override."""
        override = ChronologyOverride(project_id=5, first_commit=date(2020, 1, 1))
        assert override.project_id == 5
        assert override.first_commit == date(2020, 1, 1)
        assert override.last_commit is None

    def test_valid_with_last_commit_only(self):
        """ChronologyOverride can have only last_commit override."""
        override = ChronologyOverride(project_id=10, last_commit=date(2023, 12, 31))
        assert override.project_id == 10
        assert override.first_commit is None
        assert override.last_commit == date(2023, 12, 31)

    def test_valid_with_both_dates(self):
        """ChronologyOverride can have both first_commit and last_commit."""
        override = ChronologyOverride(
            project_id=3,
            first_commit=date(2020, 6, 15),
            last_commit=date(2023, 6, 15)
        )
        assert override.project_id == 3
        assert override.first_commit == date(2020, 6, 15)
        assert override.last_commit == date(2023, 6, 15)

    def test_parse_dates_as_strings(self):
        """ChronologyOverride should parse date strings in YYYY-MM-DD format."""
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
        """ChronologyOverride should reject invalid date formats."""
        with pytest.raises(ValidationError):
            ChronologyOverride(project_id=1, first_commit="01/01/2020")

    def test_project_id_as_various_types(self):
        """ChronologyOverride accepts integer project_id."""
        override = ChronologyOverride(project_id=999)
        assert override.project_id == 999
        assert isinstance(override.project_id, int)

    def test_negative_project_id_allowed(self):
        """ChronologyOverride allows negative project_id (no validation constraint)."""
        override = ChronologyOverride(project_id=-1)
        assert override.project_id == -1

    def test_zero_project_id_allowed(self):
        """ChronologyOverride allows zero project_id."""
        override = ChronologyOverride(project_id=0)
        assert override.project_id == 0

    def test_large_project_id(self):
        """ChronologyOverride accepts large integer project_id."""
        override = ChronologyOverride(project_id=999999999)
        assert override.project_id == 999999999

    def test_dates_dont_need_to_be_chronological(self):
        """ChronologyOverride does not enforce that first_commit <= last_commit."""
        # Model doesn't validate chronological order
        override = ChronologyOverride(
            project_id=1,
            first_commit=date(2023, 12, 31),
            last_commit=date(2020, 1, 1)
        )
        assert override.first_commit == date(2023, 12, 31)
        assert override.last_commit == date(2020, 1, 1)

    def test_model_dump(self):
        """ChronologyOverride correctly dumps to dict."""
        override = ChronologyOverride(
            project_id=5,
            first_commit=date(2020, 1, 1),
            last_commit=date(2023, 12, 31)
        )
        dumped = override.model_dump()
        assert dumped["project_id"] == 5
        assert dumped["first_commit"] == date(2020, 1, 1)
        assert dumped["last_commit"] == date(2023, 12, 31)

    def test_model_dump_with_none_dates(self):
        """ChronologyOverride.model_dump includes None values for optional dates."""
        override = ChronologyOverride(project_id=2)
        dumped = override.model_dump()
        assert dumped["first_commit"] is None
        assert dumped["last_commit"] is None


class TestCustomRanking:
    """Tests for the CustomRanking model."""

    def test_requires_project_id(self):
        """CustomRanking must have a project_id."""
        with pytest.raises(ValidationError) as exc_info:
            CustomRanking(rank=1)
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("project_id",) for e in errors)

    def test_requires_rank(self):
        """CustomRanking must have a rank."""
        with pytest.raises(ValidationError) as exc_info:
            CustomRanking(project_id=1)
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("rank",) for e in errors)

    def test_valid_with_project_id_and_rank(self):
        """CustomRanking is valid with project_id and rank."""
        ranking = CustomRanking(project_id=1, rank=1)
        assert ranking.project_id == 1
        assert ranking.rank == 1

    def test_rank_minimum_value_is_one(self):
        """CustomRanking requires rank >= 1."""
        with pytest.raises(ValidationError) as exc_info:
            CustomRanking(project_id=1, rank=0)
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("rank",) for e in errors)

    def test_rank_negative_value_rejected(self):
        """CustomRanking rejects negative rank values."""
        with pytest.raises(ValidationError) as exc_info:
            CustomRanking(project_id=1, rank=-1)
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("rank",) for e in errors)

    def test_valid_rank_of_one(self):
        """CustomRanking accepts rank=1 (minimum valid value)."""
        ranking = CustomRanking(project_id=5, rank=1)
        assert ranking.rank == 1

    def test_valid_large_rank(self):
        """CustomRanking accepts large rank values."""
        ranking = CustomRanking(project_id=10, rank=1000000)
        assert ranking.rank == 1000000

    def test_project_id_can_be_negative(self):
        """CustomRanking allows negative project_id (no validation constraint)."""
        ranking = CustomRanking(project_id=-1, rank=1)
        assert ranking.project_id == -1

    def test_project_id_can_be_zero(self):
        """CustomRanking allows zero project_id."""
        ranking = CustomRanking(project_id=0, rank=1)
        assert ranking.project_id == 0

    def test_large_project_id(self):
        """CustomRanking accepts large integer project_id."""
        ranking = CustomRanking(project_id=999999999, rank=5)
        assert ranking.project_id == 999999999

    def test_multiple_rankings_for_same_project(self):
        """Multiple CustomRanking instances can exist for the same project_id."""
        ranking1 = CustomRanking(project_id=1, rank=1)
        ranking2 = CustomRanking(project_id=1, rank=2)
        assert ranking1.project_id == ranking2.project_id
        assert ranking1.rank != ranking2.rank

    def test_model_dump(self):
        """CustomRanking correctly dumps to dict."""
        ranking = CustomRanking(project_id=7, rank=3)
        dumped = ranking.model_dump()
        assert dumped["project_id"] == 7
        assert dumped["rank"] == 3

    def test_json_serialization(self):
        """CustomRanking can be serialized to JSON string."""
        ranking = CustomRanking(project_id=42, rank=2)
        json_str = ranking.model_dump_json()
        assert '"project_id":42' in json_str
        assert '"rank":2' in json_str



