"""Tests for infra_signals_bridge extractor."""

from datetime import date

from artifactminer.evidence.extractors.infra_signals_bridge import (
    infra_signals_to_evidence,
)
from artifactminer.skills.deep_analysis import InfraSignalsResult


def test_infra_signals_to_evidence_returns_empty_for_no_tools():
    infra = InfraSignalsResult()
    result = infra_signals_to_evidence(infra)
    assert result == []


def test_infra_signals_to_evidence_converts_ci_cd_tools():
    infra = InfraSignalsResult(
        ci_cd_tools=["GitHub Actions", "GitLab CI"],
        all_tools=["GitHub Actions", "GitLab CI"],
    )
    result = infra_signals_to_evidence(infra)

    assert len(result) >= 1
    ci_cd_item = next(
        (i for i in result if i.type == "metric" and "CI/CD" in i.content), None
    )
    assert ci_cd_item is not None
    assert "GitHub Actions" in ci_cd_item.content
    assert "GitLab CI" in ci_cd_item.content


def test_infra_signals_to_evidence_converts_docker_tools():
    infra = InfraSignalsResult(
        docker_tools=["Docker", "Docker Compose"],
        all_tools=["Docker", "Docker Compose"],
    )
    result = infra_signals_to_evidence(infra)

    docker_item = next((i for i in result if "Containerization" in i.content), None)
    assert docker_item is not None
    assert "Docker" in docker_item.content


def test_infra_signals_to_evidence_converts_env_build_tools():
    infra = InfraSignalsResult(
        env_build_tools=["Make", "Terraform"],
        all_tools=["Make", "Terraform"],
    )
    result = infra_signals_to_evidence(infra)

    build_item = next((i for i in result if "Build/Deploy" in i.content), None)
    assert build_item is not None
    assert "Make" in build_item.content
    assert "Terraform" in build_item.content


def test_infra_signals_to_evidence_uses_evidence_date():
    infra = InfraSignalsResult(
        ci_cd_tools=["GitHub Actions"],
        all_tools=["GitHub Actions"],
    )
    evidence_date = date(2024, 6, 1)
    result = infra_signals_to_evidence(infra, evidence_date=evidence_date)

    assert all(item.date == evidence_date for item in result)
