"""
Config/infra fingerprint extractor — toolchain discipline signals.

Detects linters, formatters, test frameworks, build tools, deployment
tools, package managers, and pre-commit hooks from config files.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..models import ConfigFingerprint

# ---------------------------------------------------------------------------
# Config file detection patterns
# ---------------------------------------------------------------------------

# pyproject.toml tool sections → category
_PYPROJECT_TOOL_MAP: Dict[str, tuple[str, str]] = {
    "ruff": ("linters", "ruff"),
    "black": ("formatters", "black"),
    "isort": ("formatters", "isort"),
    "pytest": ("test_frameworks", "pytest"),
    "mypy": ("linters", "mypy"),
    "pylint": ("linters", "pylint"),
    "flake8": ("linters", "flake8"),
    "coverage": ("test_frameworks", "coverage"),
    "setuptools": ("build_tools", "setuptools"),
    "hatch": ("build_tools", "hatch"),
    "pdm": ("package_managers", "pdm"),
}

# package.json devDependencies → category
_NPM_DEV_DEP_MAP: Dict[str, tuple[str, str]] = {
    "eslint": ("linters", "ESLint"),
    "prettier": ("formatters", "Prettier"),
    "jest": ("test_frameworks", "Jest"),
    "mocha": ("test_frameworks", "Mocha"),
    "vitest": ("test_frameworks", "Vitest"),
    "webpack": ("build_tools", "Webpack"),
    "vite": ("build_tools", "Vite"),
    "rollup": ("build_tools", "Rollup"),
    "esbuild": ("build_tools", "esbuild"),
    "typescript": ("linters", "TypeScript"),
    "husky": ("linters", "Husky"),
    "lint-staged": ("linters", "lint-staged"),
    "cypress": ("test_frameworks", "Cypress"),
    "playwright": ("test_frameworks", "Playwright"),
}

# Lock file → package manager
_LOCK_FILE_MAP: Dict[str, str] = {
    "uv.lock": "uv",
    "poetry.lock": "Poetry",
    "Pipfile.lock": "Pipenv",
    "package-lock.json": "npm",
    "yarn.lock": "Yarn",
    "pnpm-lock.yaml": "pnpm",
    "bun.lockb": "Bun",
    "Cargo.lock": "Cargo",
    "go.sum": "Go Modules",
    "Gemfile.lock": "Bundler",
}


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------


def _parse_pyproject_toml(filepath: Path) -> Dict[str, List[str]]:
    """Extract tool information from pyproject.toml (regex, no toml lib needed)."""
    result: Dict[str, List[str]] = {}
    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return result

    for tool_name, (category, display_name) in _PYPROJECT_TOOL_MAP.items():
        # Check for [tool.X] section
        pattern = rf"\[tool\.{re.escape(tool_name)}"
        if re.search(pattern, content):
            result.setdefault(category, []).append(display_name)

    # Check for build system
    if "[build-system]" in content:
        if "hatchling" in content:
            result.setdefault("build_tools", []).append("Hatchling")
        elif "setuptools" in content:
            result.setdefault("build_tools", []).append("setuptools")
        elif "flit" in content:
            result.setdefault("build_tools", []).append("Flit")
        elif "pdm" in content:
            result.setdefault("build_tools", []).append("PDM")

    return result


def _parse_package_json(filepath: Path) -> Dict[str, List[str]]:
    """Extract tool information from package.json devDependencies."""
    result: Dict[str, List[str]] = {}
    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return result

    # Simple regex extraction of devDependencies keys (avoids json parsing issues)
    dev_deps_match = re.search(
        r'"devDependencies"\s*:\s*\{([^}]*)\}', content, re.DOTALL
    )
    if not dev_deps_match:
        return result

    deps_block = dev_deps_match.group(1)
    dep_names = re.findall(r'"(@?[\w/.-]+)"', deps_block)

    for dep in dep_names:
        # Strip scope prefix for matching
        base_name = dep.split("/")[-1] if dep.startswith("@") else dep
        for key, (category, display_name) in _NPM_DEV_DEP_MAP.items():
            if key in base_name.lower():
                result.setdefault(category, []).append(display_name)
                break

    return result


def _parse_pre_commit_config(filepath: Path) -> List[str]:
    """Extract hook IDs from .pre-commit-config.yaml."""
    hooks: List[str] = []
    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return hooks

    # Extract hook ids: "- id: <hook-name>"
    for m in re.finditer(r"-\s*id:\s*(\S+)", content):
        hook_id = m.group(1)
        if hook_id not in hooks:
            hooks.append(hook_id)

    return hooks


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_config_fingerprint(
    repo_path: str,
    infra_signals: Optional[Any] = None,
) -> ConfigFingerprint:
    """
    Extract config/infra fingerprint from repository config files.

    Args:
        repo_path: Path to the git repository root
        infra_signals: Optional InfraSignalsResult from DeepRepoAnalyzer
                       (already computed in pipeline) for CI/Docker tools

    Returns:
        ConfigFingerprint with detected tooling
    """
    root = Path(repo_path)
    fp = ConfigFingerprint()

    # Parse pyproject.toml
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        info = _parse_pyproject_toml(pyproject)
        fp.linters.extend(info.get("linters", []))
        fp.formatters.extend(info.get("formatters", []))
        fp.test_frameworks.extend(info.get("test_frameworks", []))
        fp.build_tools.extend(info.get("build_tools", []))
        fp.package_managers.extend(info.get("package_managers", []))

    # Parse package.json
    package_json = root / "package.json"
    if package_json.exists():
        info = _parse_package_json(package_json)
        fp.linters.extend(info.get("linters", []))
        fp.formatters.extend(info.get("formatters", []))
        fp.test_frameworks.extend(info.get("test_frameworks", []))
        fp.build_tools.extend(info.get("build_tools", []))

    # Parse .pre-commit-config.yaml
    pre_commit = root / ".pre-commit-config.yaml"
    if pre_commit.exists():
        fp.pre_commit_hooks = _parse_pre_commit_config(pre_commit)

    # Detect package manager from lock files
    for lock_file, manager in _LOCK_FILE_MAP.items():
        if (root / lock_file).exists():
            if manager not in fp.package_managers:
                fp.package_managers.append(manager)

    # Merge infra_signals from DeepRepoAnalyzer (CI/Docker tools)
    if infra_signals is not None:
        ci_tools = getattr(infra_signals, "ci_tools", None)
        if ci_tools:
            for tool in ci_tools:
                if tool not in fp.deployment_tools:
                    fp.deployment_tools.append(tool)

        docker = getattr(infra_signals, "has_docker", False)
        if docker and "Docker" not in fp.deployment_tools:
            fp.deployment_tools.append("Docker")

        compose = getattr(infra_signals, "has_docker_compose", False)
        if compose and "Docker Compose" not in fp.deployment_tools:
            fp.deployment_tools.append("Docker Compose")

    # Detect deployment tools from common files
    if (root / "Dockerfile").exists() and "Docker" not in fp.deployment_tools:
        fp.deployment_tools.append("Docker")
    if (root / "docker-compose.yml").exists() or (root / "docker-compose.yaml").exists():
        if "Docker Compose" not in fp.deployment_tools:
            fp.deployment_tools.append("Docker Compose")
    if (root / ".github" / "workflows").is_dir():
        if "GitHub Actions" not in fp.deployment_tools:
            fp.deployment_tools.append("GitHub Actions")
    if (root / ".gitlab-ci.yml").exists():
        if "GitLab CI" not in fp.deployment_tools:
            fp.deployment_tools.append("GitLab CI")

    # Deduplicate all lists
    fp.linters = list(dict.fromkeys(fp.linters))
    fp.formatters = list(dict.fromkeys(fp.formatters))
    fp.test_frameworks = list(dict.fromkeys(fp.test_frameworks))
    fp.build_tools = list(dict.fromkeys(fp.build_tools))
    fp.deployment_tools = list(dict.fromkeys(fp.deployment_tools))
    fp.package_managers = list(dict.fromkeys(fp.package_managers))

    return fp
