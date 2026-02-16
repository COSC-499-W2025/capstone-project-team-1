"""Unit tests for infra_signals module."""

from pathlib import Path
from unittest.mock import patch

import pytest

from artifactminer.skills.signals.infra_signals import (
    detect_ci_cd,
    detect_docker,
    detect_env_build,
    get_infra_signals,
)


class TestDetectCiCd:
    def test_detects_github_actions_workflows(self, tmp_path):
        workflow_dir = tmp_path / ".github" / "workflows"
        workflow_dir.mkdir(parents=True)
        (workflow_dir / "ci.yml").write_text("name: CI\n")

        result = detect_ci_cd(str(tmp_path))

        assert len(result) == 1
        assert result[0]["tool"] == "GitHub Actions"
        assert result[0]["evidence_type"] == "ci_cd"

    def test_detects_gitlab_ci(self, tmp_path):
        (tmp_path / ".gitlab-ci.yml").write_text("stages:\n  - build\n")

        result = detect_ci_cd(str(tmp_path))

        assert len(result) == 1
        assert result[0]["tool"] == "GitLab CI"

    def test_detects_multiple_ci_tools(self, tmp_path):
        (tmp_path / ".gitlab-ci.yml").write_text("stages: []\n")
        (tmp_path / "Jenkinsfile").write_text("pipeline {}\n")

        result = detect_ci_cd(str(tmp_path))

        tools = {r["tool"] for r in result}
        assert "GitLab CI" in tools
        assert "Jenkins" in tools

    def test_filters_by_touched_paths(self, tmp_path):
        (tmp_path / ".gitlab-ci.yml").write_text("stages: []\n")

        result = detect_ci_cd(str(tmp_path), touched_paths={"other_file.py"})

        assert len(result) == 0


class TestDetectDocker:
    def test_detects_dockerfile(self, tmp_path):
        (tmp_path / "Dockerfile").write_text("FROM python:3.11\n")

        result = detect_docker(str(tmp_path))

        assert len(result) == 1
        assert result[0]["tool"] == "Docker"
        assert result[0]["evidence_type"] == "docker"

    def test_detects_docker_compose(self, tmp_path):
        (tmp_path / "docker-compose.yml").write_text("services:\n  web:\n")

        result = detect_docker(str(tmp_path))

        assert len(result) == 1
        assert result[0]["tool"] == "Docker Compose"

    def test_detects_nested_dockerfiles(self, tmp_path):
        nested = tmp_path / "services" / "api"
        nested.mkdir(parents=True)
        (nested / "Dockerfile").write_text("FROM node:18\n")

        result = detect_docker(str(tmp_path))

        assert len(result) == 1
        assert "services/api/Dockerfile" in result[0]["path"]

    def test_filters_by_touched_paths(self, tmp_path):
        (tmp_path / "Dockerfile").write_text("FROM python:3.11\n")

        result = detect_docker(str(tmp_path), touched_paths={"other_file.py"})

        assert len(result) == 0


class TestDetectEnvBuild:
    def test_detects_makefile(self, tmp_path):
        (tmp_path / "Makefile").write_text("build:\n\techo build\n")

        result = detect_env_build(str(tmp_path))

        assert any(r["tool"] == "Make" for r in result)

    def test_detects_terraform_directory(self, tmp_path):
        terraform_dir = tmp_path / "terraform"
        terraform_dir.mkdir()
        (terraform_dir / "main.tf").write_text('resource "aws_s3_bucket" "b" {}\n')

        result = detect_env_build(str(tmp_path))

        assert any(r["tool"] == "Terraform" for r in result)

    def test_detects_kubernetes_directory(self, tmp_path):
        k8s_dir = tmp_path / "k8s"
        k8s_dir.mkdir()
        (k8s_dir / "deployment.yaml").write_text("apiVersion: apps/v1\n")

        result = detect_env_build(str(tmp_path))

        assert any(r["tool"] == "Kubernetes" for r in result)

    def test_detects_env_files(self, tmp_path):
        (tmp_path / ".env").write_text("API_KEY=secret\n")
        (tmp_path / ".env.example").write_text("API_KEY=\n")

        result = detect_env_build(str(tmp_path))

        tools = {r["tool"] for r in result}
        assert "Environment Variables" in tools
        assert "Environment Variables Template" in tools


class TestGetInfraSignals:
    def test_aggregates_all_signal_types(self, tmp_path):
        (tmp_path / "Dockerfile").write_text("FROM python:3.11\n")
        (tmp_path / "Makefile").write_text("build:\n")
        workflow_dir = tmp_path / ".github" / "workflows"
        workflow_dir.mkdir(parents=True)
        (workflow_dir / "ci.yml").write_text("name: CI\n")

        result = get_infra_signals(str(tmp_path))

        assert "ci_cd" in result
        assert "docker" in result
        assert "env_build" in result
        assert "summary" in result

        summary = result["summary"]
        assert "GitHub Actions" in summary["ci_cd_tools"]
        assert "Docker" in summary["docker_tools"]
        assert "Make" in summary["env_build_tools"]
        assert "GitHub Actions" in summary["all_tools"]
        assert "Docker" in summary["all_tools"]
        assert "Make" in summary["all_tools"]

    def test_returns_empty_lists_for_empty_repo(self, tmp_path):
        result = get_infra_signals(str(tmp_path))

        assert result["ci_cd"] == []
        assert result["docker"] == []
        assert result["env_build"] == []
        assert result["summary"]["all_tools"] == []
