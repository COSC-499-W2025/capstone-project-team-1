"""
Framework Detection Module for Repository Intelligence
Detects frameworks by analyzing dependency files and configuration files
"""

from pathlib import Path
from typing import List
import json
import re


def detect_python_frameworks(repo_path: str) -> List[str]:
    """
    Detect Python frameworks by analyzing:
    - requirements.txt
    - pyproject.toml
    - Pipfile
    - setup.py
    """
    frameworks = []
    repo_path = Path(repo_path)

    # Framework patterns for Python
    python_frameworks = {
        'Django': ['django'],
        'Flask': ['flask'],
        'FastAPI': ['fastapi'],
        'SQLAlchemy': ['sqlalchemy'],
        'Pytest': ['pytest'],
        'Celery': ['celery'],
        'Pydantic': ['pydantic'],
        'aiohttp': ['aiohttp'],
    }

    # Check requirements.txt
    requirements_path = repo_path / 'requirements.txt'
    if requirements_path.exists():
        try:
            with open(requirements_path, 'r') as f:
                content = f.read().lower()
                for framework, patterns in python_frameworks.items():
                    for pattern in patterns:
                        if pattern in content:
                            if framework not in frameworks:
                                frameworks.append(framework)
                            break
        except Exception:
            pass

    # Check pyproject.toml
    pyproject_path = repo_path / 'pyproject.toml'
    if pyproject_path.exists():
        try:
            with open(pyproject_path, 'r') as f:
                content = f.read().lower()
                for framework, patterns in python_frameworks.items():
                    for pattern in patterns:
                        if pattern in content:
                            if framework not in frameworks:
                                frameworks.append(framework)
                            break
        except Exception:
            pass

    # Check Pipfile
    pipfile_path = repo_path / 'Pipfile'
    if pipfile_path.exists():
        try:
            with open(pipfile_path, 'r') as f:
                content = f.read().lower()
                for framework, patterns in python_frameworks.items():
                    for pattern in patterns:
                        if pattern in content:
                            if framework not in frameworks:
                                frameworks.append(framework)
                            break
        except Exception:
            pass

    # Check setup.py
    setup_path = repo_path / 'setup.py'
    if setup_path.exists():
        try:
            with open(setup_path, 'r') as f:
                content = f.read().lower()
                for framework, patterns in python_frameworks.items():
                    for pattern in patterns:
                        if pattern in content:
                            if framework not in frameworks:
                                frameworks.append(framework)
                            break
        except Exception:
            pass

    return frameworks


def detect_javascript_frameworks(repo_path: str) -> List[str]:
    """
    Detect JavaScript/TypeScript frameworks by analyzing:
    - package.json
    """
    frameworks = []
    repo_path = Path(repo_path)

    # Framework patterns for JavaScript
    js_frameworks = {
        'React': ['react'],
        'Vue': ['vue'],
        'Angular': ['@angular/core'],
        'Express': ['express'],
        'Next.js': ['next'],
        'Nest.js': ['@nestjs/common'],
        'Svelte': ['svelte'],
        'Nuxt': ['nuxt'],
        'Webpack': ['webpack'],
        'Vite': ['vite'],
        'Jest': ['jest'],
        'Mocha': ['mocha'],
        'TypeScript': ['typescript'],
    }

    # Check package.json
    package_path = repo_path / 'package.json'
    if package_path.exists():
        try:
            with open(package_path, 'r') as f:
                package_data = json.load(f)
                # Check in dependencies
                dependencies = package_data.get('dependencies', {})
                dev_dependencies = package_data.get('devDependencies', {})

                all_deps = {**dependencies, **dev_dependencies}

                for framework, patterns in js_frameworks.items():
                    for pattern in patterns:
                        if pattern in all_deps:
                            if framework not in frameworks:
                                frameworks.append(framework)
                            break
        except Exception:
            pass

    return frameworks


def detect_java_frameworks(repo_path: str) -> List[str]:
    """
    Detect Java frameworks by analyzing:
    - pom.xml
    - build.gradle
    """
    frameworks = []
    repo_path = Path(repo_path)

    # Framework patterns for Java
    java_frameworks = {
        'Spring': ['spring-boot', 'spring-core', 'spring-context'],
        'Hibernate': ['hibernate'],
        'JUnit': ['junit'],
        'Gradle': ['gradle'],
        'Maven': ['maven'],
    }

    # Check pom.xml
    pom_path = repo_path / 'pom.xml'
    if pom_path.exists():
        try:
            with open(pom_path, 'r') as f:
                content = f.read().lower()
                for framework, patterns in java_frameworks.items():
                    for pattern in patterns:
                        if pattern in content:
                            if framework not in frameworks:
                                frameworks.append(framework)
                            break
        except Exception:
            pass

    # Check build.gradle
    gradle_path = repo_path / 'build.gradle'
    if gradle_path.exists():
        try:
            with open(gradle_path, 'r') as f:
                content = f.read().lower()
                for framework, patterns in java_frameworks.items():
                    for pattern in patterns:
                        if pattern in content:
                            if framework not in frameworks:
                                frameworks.append(framework)
                            break
        except Exception:
            pass

    # Check for build.gradle.kts (Kotlin DSL)
    gradle_kts_path = repo_path / 'build.gradle.kts'
    if gradle_kts_path.exists():
        try:
            with open(gradle_kts_path, 'r') as f:
                content = f.read().lower()
                for framework, patterns in java_frameworks.items():
                    for pattern in patterns:
                        if pattern in content:
                            if framework not in frameworks:
                                frameworks.append(framework)
                            break
        except Exception:
            pass

    return frameworks


def detect_go_frameworks(repo_path: str) -> List[str]:
    """
    Detect Go frameworks by analyzing:
    - go.mod
    """
    frameworks = []
    repo_path = Path(repo_path)

    # Framework patterns for Go
    go_frameworks = {
        'Gin': ['gin-gonic/gin'],
        'Echo': ['echo'],
        'Fiber': ['fiber'],
        'Beego': ['beego'],
        'GORM': ['gorm'],
    }

    # Check go.mod
    go_mod_path = repo_path / 'go.mod'
    if go_mod_path.exists():
        try:
            with open(go_mod_path, 'r') as f:
                content = f.read().lower()
                for framework, patterns in go_frameworks.items():
                    for pattern in patterns:
                        if pattern in content:
                            if framework not in frameworks:
                                frameworks.append(framework)
                            break
        except Exception:
            pass

    return frameworks


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

    # Detect frameworks for each language
    all_frameworks.extend(detect_python_frameworks(repo_path))
    all_frameworks.extend(detect_javascript_frameworks(repo_path))
    all_frameworks.extend(detect_java_frameworks(repo_path))
    all_frameworks.extend(detect_go_frameworks(repo_path))

    # Remove duplicates while preserving order
    seen = set()
    unique_frameworks = []
    for framework in all_frameworks:
        if framework not in seen:
            seen.add(framework)
            unique_frameworks.append(framework)

    return unique_frameworks
