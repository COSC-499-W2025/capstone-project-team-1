"""Pattern definitions and constants used for skill extraction."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence

# Canonical categories for reporting
CATEGORIES = {
    "languages": "Programming Languages",
    "frameworks": "Frameworks & Libraries",
    "practices": "Software Engineering Practices",
    "algorithms": "Data Structures & Algorithms",
    "tools": "Tools & Platforms",
}


@dataclass(frozen=True)
class CodePattern:
    """Regex-based pattern to infer a skill from code snippets or additions."""

    skill: str
    regex: str
    category: str
    evidence: str
    weight: float = 0.6


@dataclass(frozen=True)
class FilePattern:
    """Filesystem-based signal for a skill."""

    paths: Sequence[str]
    skill: str
    category: str
    evidence: str
    weight: float = 0.55


LANGUAGE_EXTENSIONS: Dict[str, tuple[str, str]] = {
    ".py": ("Python", CATEGORIES["languages"]),
    ".js": ("JavaScript", CATEGORIES["languages"]),
    ".ts": ("TypeScript", CATEGORIES["languages"]),
    ".jsx": ("JavaScript", CATEGORIES["languages"]),
    ".tsx": ("TypeScript", CATEGORIES["languages"]),
    ".java": ("Java", CATEGORIES["languages"]),
    ".kt": ("Kotlin", CATEGORIES["languages"]),
    ".go": ("Go", CATEGORIES["languages"]),
    ".rs": ("Rust", CATEGORIES["languages"]),
    ".c": ("C", CATEGORIES["languages"]),
    ".cpp": ("C++", CATEGORIES["languages"]),
    ".cs": ("C#", CATEGORIES["languages"]),
    ".rb": ("Ruby", CATEGORIES["languages"]),
    ".php": ("PHP", CATEGORIES["languages"]),
    ".swift": ("Swift", CATEGORIES["languages"]),
    ".sql": ("SQL", CATEGORIES["languages"]),
    ".sh": ("Shell Scripting", CATEGORIES["languages"]),
    ".ps1": ("PowerShell", CATEGORIES["languages"]),
    ".md": ("Technical Writing", CATEGORIES["practices"]),
}

# Dependency names we care about (parsed from common manifests)
# Keep this list high-signal and multi-language; evidence is added in extractor.
DEPENDENCY_SKILLS: Dict[str, tuple[str, str]] = {
    # Python web/backend
    "fastapi": ("FastAPI", CATEGORIES["frameworks"]),
    "uvicorn": ("FastAPI", CATEGORIES["frameworks"]),
    "starlette": ("FastAPI", CATEGORIES["frameworks"]),
    "httptools": ("FastAPI", CATEGORIES["frameworks"]),
    "flask": ("Flask", CATEGORIES["frameworks"]),
    "django": ("Django", CATEGORIES["frameworks"]),
    # Python data/ML
    "numpy": ("Numerical Computing", CATEGORIES["frameworks"]),
    "pandas": ("Data Analysis", CATEGORIES["frameworks"]),
    "scikit-learn": ("Machine Learning", CATEGORIES["frameworks"]),
    "torch": ("Deep Learning (PyTorch)", CATEGORIES["frameworks"]),
    "tensorflow": ("Deep Learning (TensorFlow)", CATEGORIES["frameworks"]),
    # Python infra/testing/utilities
    "sqlalchemy": ("SQLAlchemy", CATEGORIES["frameworks"]),
    "alembic": ("Database Migrations", CATEGORIES["tools"]),
    "pydantic": ("Data Validation", CATEGORIES["frameworks"]),
    "pytest": ("Testing", CATEGORIES["practices"]),
    "pytest-asyncio": ("Async Testing", CATEGORIES["practices"]),
    "httpx": ("HTTP Clients", CATEGORIES["frameworks"]),
    "openai": ("LLM Integration", CATEGORIES["tools"]),
    "gitpython": ("Git Automation", CATEGORIES["tools"]),
    "aiosqlite": ("Async Datastores", CATEGORIES["frameworks"]),
    "email-validator": ("Input Validation", CATEGORIES["practices"]),
    "python-multipart": ("File Upload Handling", CATEGORIES["practices"]),
    "celery": ("Task Queues", CATEGORIES["tools"]),
    "redis": ("Caching", CATEGORIES["tools"]),
    "kafka": ("Message Queues", CATEGORIES["tools"]),
    # JavaScript / TypeScript
    "react": ("React", CATEGORIES["frameworks"]),
    "vue": ("Vue", CATEGORIES["frameworks"]),
    "@angular/core": ("Angular", CATEGORIES["frameworks"]),
    "next": ("Next.js", CATEGORIES["frameworks"]),
    "express": ("Express", CATEGORIES["frameworks"]),
    "@nestjs/common": ("NestJS", CATEGORIES["frameworks"]),
    "jest": ("Testing", CATEGORIES["practices"]),
    "vitest": ("Testing", CATEGORIES["practices"]),
    "webpack": ("Build Tooling", CATEGORIES["tools"]),
    "vite": ("Build Tooling", CATEGORIES["tools"]),
    "typescript": ("TypeScript", CATEGORIES["languages"]),
    # Java / JVM
    "spring-boot": ("Spring Boot", CATEGORIES["frameworks"]),
    "spring-core": ("Spring", CATEGORIES["frameworks"]),
    "hibernate": ("Hibernate", CATEGORIES["frameworks"]),
    "junit": ("Testing", CATEGORIES["practices"]),
    # Go
    "github.com/gin-gonic/gin": ("Gin", CATEGORIES["frameworks"]),
    "github.com/labstack/echo": ("Echo", CATEGORIES["frameworks"]),
    "github.com/gofiber/fiber": ("Fiber", CATEGORIES["frameworks"]),
    "gorm.io/gorm": ("GORM", CATEGORIES["frameworks"]),
}

FILE_PATTERNS: List[FilePattern] = [
    FilePattern(
        paths=["Dockerfile", "docker-compose.yml", "docker-compose.yaml"],
        skill="Containerization",
        category=CATEGORIES["tools"],
        evidence="Docker configuration present",
        weight=0.65,
    ),
    FilePattern(
        paths=[".github/workflows"],
        skill="CI/CD",
        category=CATEGORIES["practices"],
        evidence="GitHub Actions workflows present",
        weight=0.65,
    ),
    FilePattern(
        paths=["requirements.txt", "pyproject.toml"],
        skill="Dependency Management",
        category=CATEGORIES["practices"],
        evidence="Python dependency manifest present",
    ),
    FilePattern(
        paths=["alembic.ini", "alembic"],
        skill="Database Migrations",
        category=CATEGORIES["tools"],
        evidence="Alembic migration config present",
        weight=0.62,
    ),
    FilePattern(
        paths=["tests", "pytest.ini", "pyproject.toml"],
        skill="Automated Testing",
        category=CATEGORIES["practices"],
        evidence="Test suite present",
        weight=0.62,
    ),
    FilePattern(
        paths=["README.md", "docs"],
        skill="Documentation",
        category=CATEGORIES["practices"],
        evidence="Project documentation present",
        weight=0.55,
    ),
]

CODE_REGEX_PATTERNS: List[CodePattern] = [
    CodePattern(
        skill="Asynchronous Programming",
        regex=r"\basync\s+def\b",
        category=CATEGORIES["practices"],
        evidence="async def usage in changes",
    ),
    CodePattern(
        skill="Error Handling",
        regex=r"class\s+.*Exception",
        category=CATEGORIES["practices"],
        evidence="Custom exception detected",
    ),
    CodePattern(
        skill="SQL",
        regex=r"SELECT\s+.*\s+FROM",
        category=CATEGORIES["frameworks"],
        evidence="SQL query found in changes",
    ),
    CodePattern(
        skill="Unit Testing",
        regex=r"import\s+unittest|pytest\.",
        category=CATEGORIES["practices"],
        evidence="Testing imports detected",
    ),
    CodePattern(
        skill="REST API Design",
        regex=r"@router\.(get|post|put|delete)",
        category=CATEGORIES["frameworks"],
        evidence="HTTP route handlers detected",
    ),
    CodePattern(
        skill="Data Validation",
        regex=r"pydantic\.BaseModel|from\s+pydantic\s+import",
        category=CATEGORIES["frameworks"],
        evidence="Pydantic models referenced",
    ),
    CodePattern(
        skill="Dependency Injection",
        regex=r"Depends\(",
        category=CATEGORIES["practices"],
        evidence="FastAPI Depends used",
    ),
    CodePattern(
        skill="Logging",
        regex=r"logging\.",
        category=CATEGORIES["practices"],
        evidence="Logging statements present",
    ),
    CodePattern(
        skill="Command Line Tools",
        regex=r"argparse|click",
        category=CATEGORIES["tools"],
        evidence="CLI parsing detected",
    ),
    CodePattern(
        skill="Configuration Management",
        regex=r"dotenv|os\.getenv",
        category=CATEGORIES["practices"],
        evidence="Env var configuration detected",
    ),
]

GIT_SKILLS = [
    {
        "key": "merge_commits",
        "skill": "Version Control",
        "category": CATEGORIES["practices"],
        "evidence": "Merge commits found",
        "weight": 0.55,
    },
    {
        "key": "branches",
        "skill": "Branching Strategies",
        "category": CATEGORIES["practices"],
        "evidence": "Multiple branches present",
        "weight": 0.52,
    },
]
