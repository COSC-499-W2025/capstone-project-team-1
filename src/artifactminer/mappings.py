"""Shared mappings for dependency-based skill and framework detection."""

from __future__ import annotations

from typing import Dict

# Canonical categories for reporting
CATEGORIES = {
    "languages": "Programming Languages",
    "frameworks": "Frameworks & Libraries",
    "practices": "Software Engineering Practices",
    "algorithms": "Data Structures & Algorithms",
    "tools": "Tools & Platforms",
}

# Dependency names we care about (parsed from common manifests), grouped by ecosystem.
# Values are a (skill, category) tuple.
DEPENDENCY_SKILLS: Dict[str, Dict[str, tuple[str, str]]] = {
    "python": {
        "fastapi": ("FastAPI", CATEGORIES["frameworks"]),
        "uvicorn": ("FastAPI", CATEGORIES["frameworks"]),
        "starlette": ("FastAPI", CATEGORIES["frameworks"]),
        "httptools": ("FastAPI", CATEGORIES["frameworks"]),
        "flask": ("Flask", CATEGORIES["frameworks"]),
        "django": ("Django", CATEGORIES["frameworks"]),
        "numpy": ("Numerical Computing", CATEGORIES["frameworks"]),
        "pandas": ("Data Analysis", CATEGORIES["frameworks"]),
        "scikit-learn": ("Machine Learning", CATEGORIES["frameworks"]),
        "torch": ("Deep Learning (PyTorch)", CATEGORIES["frameworks"]),
        "tensorflow": ("Deep Learning (TensorFlow)", CATEGORIES["frameworks"]),
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
    },
    "javascript": {
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
    },
    "java": {
        "spring-boot": ("Spring Boot", CATEGORIES["frameworks"]),
        "spring-core": ("Spring", CATEGORIES["frameworks"]),
        "hibernate": ("Hibernate", CATEGORIES["frameworks"]),
        "junit": ("Testing", CATEGORIES["practices"]),
    },
    "go": {
        "github.com/gin-gonic/gin": ("Gin", CATEGORIES["frameworks"]),
        "github.com/labstack/echo": ("Echo", CATEGORIES["frameworks"]),
        "github.com/gofiber/fiber": ("Fiber", CATEGORIES["frameworks"]),
        "gorm.io/gorm": ("GORM", CATEGORIES["frameworks"]),
    },
    "cross": {
        # Cross-cutting tools not tied to a single ecosystem
        "docker": ("Containerization", CATEGORIES["tools"]),
        "kubernetes": ("Container Orchestration", CATEGORIES["tools"]),
    },
}

# Pre-computed lookup of dependency needle -> framework skill per ecosystem (framework-only).
FRAMEWORK_DEPENDENCIES_BY_ECOSYSTEM: Dict[str, Dict[str, str]] = {}
for eco, mapping in DEPENDENCY_SKILLS.items():
    frameworks = {
        dep.lower(): skill
        for dep, (skill, category) in mapping.items()
        if category == CATEGORIES["frameworks"]
    }
    if frameworks:
        FRAMEWORK_DEPENDENCIES_BY_ECOSYSTEM[eco] = frameworks
