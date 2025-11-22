"""
Framework Detection Module for Repository Intelligence
Detects frameworks by analyzing dependency files and configuration files
"""

from pathlib import Path
from typing import Dict, List

import json

from artifactminer.mappings import FRAMEWORK_DEPENDENCIES_BY_ECOSYSTEM


def _framework_needles(ecosystem: str) -> Dict[str, str]:
    return FRAMEWORK_DEPENDENCIES_BY_ECOSYSTEM.get(ecosystem, {})


def _scan_text_for_frameworks(content: str, needles: Dict[str, str]) -> List[str]:
    """Return frameworks whose dependency needle appears in the provided text content."""
    found: List[str] = []
    for dep, skill in needles.items():
        if dep in content and skill not in found:
            found.append(skill)
    return found


def detect_python_frameworks(repo_path: str) -> List[str]:
    frameworks: List[str] = []
    repo_path = Path(repo_path)
    needles = _framework_needles("python")
    if not needles:
        return frameworks

    for filename in ("requirements.txt", "pyproject.toml", "Pipfile", "setup.py"):
        path = repo_path / filename
        if not path.exists():
            continue
        try:
            content = path.read_text().lower()
        except Exception:
            continue
        frameworks.extend(_scan_text_for_frameworks(content, needles))

    # preserve insertion order without duplicates
    seen = set()
    unique = []
    for fw in frameworks:
        if fw not in seen:
            seen.add(fw)
            unique.append(fw)
    return unique


def detect_javascript_frameworks(repo_path: str) -> List[str]:
    frameworks: List[str] = []
    repo_path = Path(repo_path)
    needles = _framework_needles("javascript")
    if not needles:
        return frameworks

    package_path = repo_path / "package.json"
    if not package_path.exists():
        return frameworks

    try:
        package_data = json.loads(package_path.read_text())
    except Exception:
        return frameworks

    dependencies = package_data.get("dependencies", {}) or {}
    dev_dependencies = package_data.get("devDependencies", {}) or {}
    all_deps = {**dependencies, **dev_dependencies}
    dep_keys = {k.lower() for k in all_deps.keys()}

    for dep in dep_keys:
        skill = needles.get(dep)
        if skill and skill not in frameworks:
            frameworks.append(skill)

    return frameworks


def detect_java_frameworks(repo_path: str) -> List[str]:
    frameworks: List[str] = []
    repo_path = Path(repo_path)
    needles = _framework_needles("java")
    if not needles:
        return frameworks

    for filename in ("pom.xml", "build.gradle", "build.gradle.kts"):
        path = repo_path / filename
        if not path.exists():
            continue
        try:
            content = path.read_text().lower()
        except Exception:
            continue
        frameworks.extend(_scan_text_for_frameworks(content, needles))

    seen = set()
    unique = []
    for fw in frameworks:
        if fw not in seen:
            seen.add(fw)
            unique.append(fw)
    return unique


def detect_go_frameworks(repo_path: str) -> List[str]:
    frameworks: List[str] = []
    repo_path = Path(repo_path)
    needles = _framework_needles("go")
    if not needles:
        return frameworks

    go_mod_path = repo_path / "go.mod"
    if not go_mod_path.exists():
        return frameworks
    try:
        content = go_mod_path.read_text().lower()
    except Exception:
        return frameworks

    frameworks.extend(_scan_text_for_frameworks(content, needles))
    seen = set()
    unique = []
    for fw in frameworks:
        if fw not in seen:
            seen.add(fw)
            unique.append(fw)
    return unique


def detect_frameworks(repo_path: str) -> List[str]:
    """
    Detect frameworks in a repository by analyzing:
    - package.json (JavaScript/TypeScript)
    - requirements.txt, pyproject.toml, Pipfile, setup.py (Python)
    - pom.xml, build.gradle (Java)
    - go.mod (Go)

    Args:
        repo_path: Path to the repository

    Returns:
        List of detected framework names
    """
    all_frameworks = []
    all_frameworks.extend(detect_python_frameworks(repo_path))
    all_frameworks.extend(detect_javascript_frameworks(repo_path))
    all_frameworks.extend(detect_java_frameworks(repo_path))
    all_frameworks.extend(detect_go_frameworks(repo_path))

    seen = set()
    unique_frameworks = []
    for framework in all_frameworks:
        if framework not in seen:
            seen.add(framework)
            unique_frameworks.append(framework)

    return unique_frameworks
