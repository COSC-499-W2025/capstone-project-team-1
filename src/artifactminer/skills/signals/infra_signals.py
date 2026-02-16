"""Infrastructure and DevOps configuration signals."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

from artifactminer.skills.signals.file_signals import path_in_touched


CI_CD_PATTERNS: Dict[str, Tuple[str, List[str]]] = {
    ".github/workflows": ("GitHub Actions", ["*.yml", "*.yaml"]),
    ".gitlab-ci.yml": ("GitLab CI", []),
    ".circleci/config.yml": ("CircleCI", []),
    "Jenkinsfile": ("Jenkins", []),
    "azure-pipelines.yml": ("Azure Pipelines", []),
    "azure-pipelines.yaml": ("Azure Pipelines", []),
    ".travis.yml": ("Travis CI", []),
    "bitbucket-pipelines.yml": ("Bitbucket Pipelines", []),
    "cloudbuild.yaml": ("Google Cloud Build", []),
    "cloudbuild.yml": ("Google Cloud Build", []),
}

DOCKER_PATTERNS: Dict[str, str] = {
    "Dockerfile": "Docker",
    "docker-compose.yml": "Docker Compose",
    "docker-compose.yaml": "Docker Compose",
    "docker-compose.override.yml": "Docker Compose Override",
    ".dockerignore": "Docker Ignore",
}

ENV_BUILD_PATTERNS: Dict[str, Tuple[str, str]] = {
    ".env": ("Environment Variables", "config"),
    ".env.example": ("Environment Variables Template", "config"),
    ".env.local": ("Environment Variables Local", "config"),
    "Makefile": ("Make", "build"),
    "CMakeLists.txt": ("CMake", "build"),
    "Vagrantfile": ("Vagrant", "infra"),
    "ansible.cfg": ("Ansible", "infra"),
    "terraform": ("Terraform", "infra"),
    "main.tf": ("Terraform", "infra"),
    "kubernetes": ("Kubernetes", "infra"),
    "k8s": ("Kubernetes", "infra"),
    "helm": ("Helm", "infra"),
    "Chart.yaml": ("Helm", "infra"),
    "skaffold.yaml": ("Skaffold", "infra"),
    "Procfile": ("Heroku", "deploy"),
    "vercel.json": ("Vercel", "deploy"),
    "netlify.toml": ("Netlify", "deploy"),
    "serverless.yml": ("Serverless Framework", "deploy"),
    "serverless.yaml": ("Serverless Framework", "deploy"),
    "sam.yaml": ("AWS SAM", "deploy"),
    "template.yaml": ("AWS SAM", "deploy"),
}


def detect_ci_cd(
    repo_path: str,
    *,
    touched_paths: Set[str] | None = None,
) -> List[Dict[str, Any]]:
    """Detect CI/CD configurations in the repository.

    Returns list of dicts with keys: tool, path, evidence_type
    """
    results: List[Dict[str, Any]] = []
    root = Path(repo_path)

    for pattern, (tool_name, extensions) in CI_CD_PATTERNS.items():
        if touched_paths is not None and not path_in_touched(pattern, touched_paths):
            continue

        candidate = root / pattern
        if candidate.is_file():
            results.append(
                {
                    "tool": tool_name,
                    "path": pattern,
                    "evidence_type": "ci_cd",
                }
            )
        elif candidate.is_dir():
            if extensions:
                for ext_pattern in extensions:
                    for match in candidate.glob(ext_pattern):
                        rel = str(match.relative_to(root))
                        results.append(
                            {
                                "tool": tool_name,
                                "path": rel,
                                "evidence_type": "ci_cd",
                            }
                        )
            else:
                for child in candidate.rglob("*"):
                    if child.is_file() and child.suffix in (".yml", ".yaml"):
                        rel = str(child.relative_to(root))
                        results.append(
                            {
                                "tool": tool_name,
                                "path": rel,
                                "evidence_type": "ci_cd",
                            }
                        )

    return results


def detect_docker(
    repo_path: str,
    *,
    touched_paths: Set[str] | None = None,
) -> List[Dict[str, Any]]:
    """Detect Docker-related configurations.

    Returns list of dicts with keys: tool, path, evidence_type
    """
    results: List[Dict[str, Any]] = []
    root = Path(repo_path)

    for pattern, tool_name in DOCKER_PATTERNS.items():
        if touched_paths is not None and not path_in_touched(pattern, touched_paths):
            continue

        for match in root.rglob(pattern):
            if match.is_file():
                rel = str(match.relative_to(root))
                results.append(
                    {
                        "tool": tool_name,
                        "path": rel,
                        "evidence_type": "docker",
                    }
                )

    return results


def detect_env_build(
    repo_path: str,
    *,
    touched_paths: Set[str] | None = None,
) -> List[Dict[str, Any]]:
    """Detect environment, build, and deployment configurations.

    Returns list of dicts with keys: tool, path, category, evidence_type
    """
    results: List[Dict[str, Any]] = []
    seen_entries: Set[Tuple[str, str, str]] = set()
    root = Path(repo_path)

    def _add_result(tool_name: str, rel_path: str, category: str) -> None:
        key = (tool_name, rel_path, category)
        if key in seen_entries:
            return
        seen_entries.add(key)
        results.append(
            {
                "tool": tool_name,
                "path": rel_path,
                "category": category,
                "evidence_type": "env_build",
            }
        )

    for pattern, (tool_name, category) in ENV_BUILD_PATTERNS.items():
        if touched_paths is not None and not path_in_touched(pattern, touched_paths):
            continue

        candidate = root / pattern
        if candidate.is_file():
            _add_result(tool_name, pattern, category)
        elif candidate.is_dir():
            for child in candidate.rglob("*"):
                if child.is_file():
                    rel = str(child.relative_to(root))
                    _add_result(tool_name, rel, category)
        else:
            for match in root.rglob(pattern):
                if match.is_file():
                    rel = str(match.relative_to(root))
                    _add_result(tool_name, rel, category)

    return results


def get_infra_signals(
    repo_path: str,
    *,
    touched_paths: Set[str] | None = None,
) -> Dict[str, Any]:
    """Aggregate all infrastructure signals.

    Returns dict with keys: ci_cd, docker, env_build, summary
    """
    ci_cd = detect_ci_cd(repo_path, touched_paths=touched_paths)
    docker = detect_docker(repo_path, touched_paths=touched_paths)
    env_build = detect_env_build(repo_path, touched_paths=touched_paths)

    tools = set()
    for item in ci_cd + docker + env_build:
        tools.add(item["tool"])

    return {
        "ci_cd": ci_cd,
        "docker": docker,
        "env_build": env_build,
        "summary": {
            "ci_cd_tools": [r["tool"] for r in ci_cd],
            "docker_tools": [r["tool"] for r in docker],
            "env_build_tools": [r["tool"] for r in env_build],
            "all_tools": sorted(tools),
        },
    }
