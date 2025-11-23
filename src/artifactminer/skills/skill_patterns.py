"""Pattern definitions and constants used for skill extraction."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence

from artifactminer.mappings import CATEGORIES


@dataclass(frozen=True)
class CodePattern:
    """Regex-based pattern to infer a skill from code snippets or additions."""

    skill: str
    regex: str
    category: str
    evidence: str
    weight: float = 0.6
    ecosystems: tuple[str, ...] | None = None  # e.g., ("python",)


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
        ecosystems=("python",),
    ),
    CodePattern(
        skill="Error Handling",
        regex=r"class\s+.*Exception",
        category=CATEGORIES["practices"],
        evidence="Custom exception detected",
        ecosystems=("python",),
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
        ecosystems=("python",),
    ),
    CodePattern(
        skill="REST API Design",
        regex=r"@router\.(get|post|put|delete)",
        category=CATEGORIES["frameworks"],
        evidence="HTTP route handlers detected",
        ecosystems=("python",),
    ),
    CodePattern(
        skill="Data Validation",
        regex=r"pydantic\.BaseModel|from\s+pydantic\s+import",
        category=CATEGORIES["frameworks"],
        evidence="Pydantic models referenced",
        ecosystems=("python",),
    ),
    CodePattern(
        skill="Dependency Injection",
        regex=r"Depends\(",
        category=CATEGORIES["practices"],
        evidence="FastAPI Depends used",
        ecosystems=("python",),
    ),
    CodePattern(
        skill="Logging",
        regex=r"logging\.",
        category=CATEGORIES["practices"],
        evidence="Logging statements present",
        ecosystems=None,
    ),
    CodePattern(
        skill="Command Line Tools",
        regex=r"argparse|click",
        category=CATEGORIES["tools"],
        evidence="CLI parsing detected",
        ecosystems=("python",),
    ),
    CodePattern(
        skill="Configuration Management",
        regex=r"dotenv|os\.getenv",
        category=CATEGORIES["practices"],
        evidence="Env var configuration detected",
        ecosystems=("python",),
    ),
    CodePattern(
        skill="Annotation-based APIs",
        regex=r"@RestController|@GetMapping|@PostMapping|@RequestMapping",
        category=CATEGORIES["frameworks"],
        evidence="Java/Spring REST annotations detected",
        ecosystems=("java",),
    ),
    CodePattern(
        skill="JUnit Testing",
        regex=r"@Test",
        category=CATEGORIES["practices"],
        evidence="JUnit tests detected",
        ecosystems=("java",),
    ),
    CodePattern(
        skill="TypeScript Typing",
        regex=r":\s*[A-Z][A-Za-z0-9_<>]+(?=\s*[=;,)])",
        category=CATEGORIES["practices"],
        evidence="Type annotations detected in TS/JS",
        ecosystems=("typescript", "javascript"),
    ),
]

# Additional, higher-order patterns that still operate on user additions (option 1 approach).
DEEP_CODE_PATTERNS: List[CodePattern] = [
    # Complexity / resource-awareness signals
    CodePattern(
        skill="Resource Management",
        regex=r"\b(max_\w+|limit\w*|chunk\w*|batch\w*|throttle|sample_limit|timeout)\s*[:=]",
        category=CATEGORIES["practices"],
        evidence="Resource caps or chunking present in changes",
        weight=0.68,
    ),
    # Data-structure sophistication
    CodePattern(
        skill="Advanced Collections",
        regex=r"(from\s+collections\s+import\s+|collections\.)(Counter|defaultdict|deque|OrderedDict|ChainMap)",
        category=CATEGORIES["practices"],
        evidence="Specialized Python collections in changes",
        ecosystems=("python",),
        weight=0.7,
    ),
    CodePattern(
        skill="Algorithm Optimization",
        regex=r"\b(heapq|bisect|functools\.lru_cache|@lru_cache)\b",
        category=CATEGORIES["practices"],
        evidence="Algorithmic optimization techniques in changes",
        ecosystems=("python",),
        weight=0.72,
    ),
    # Abstraction / design
    CodePattern(
        skill="Dataclass Design",
        regex=r"@dataclass|@dataclasses\.dataclass",
        category=CATEGORIES["practices"],
        evidence="Dataclass-based modeling in changes",
        ecosystems=("python",),
        weight=0.65,
    ),
    CodePattern(
        skill="Abstract Interfaces",
        regex=r"(ABC|Protocol|@abstractmethod|@abc\.abstractmethod|interface\s+I[A-Z])",
        category=CATEGORIES["practices"],
        evidence="Abstract base classes or interfaces in changes",
        weight=0.75,
    ),
    # Robustness / error handling
    CodePattern(
        skill="Exception Design",
        regex=r"class\s+\w+(Error|Exception)\(",
        category=CATEGORIES["practices"],
        evidence="Custom exception types declared in changes",
        weight=0.7,
    ),
    CodePattern(
        skill="Context Management",
        regex=r"(with\s+.+:|\bcontextmanager\b|__enter__|__exit__)",
        category=CATEGORIES["practices"],
        evidence="Context manager usage for resource safety in changes",
        ecosystems=("python",),
        weight=0.73,
    ),
]

CODE_REGEX_PATTERNS.extend(DEEP_CODE_PATTERNS)

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
