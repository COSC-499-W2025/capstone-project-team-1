# Milestone 3: Resume & Portfolio HTML Generation

## Goal

Generate two HTML deliverables from analyzed project data:

1. **One-page resume** — printable to PDF via browser print. Sections: Education/Awards, Skills by expertise level, Projects with contribution evidence.
2. **Interactive web portfolio** — opens in browser. Features: skills timeline, activity heatmap, top 3 project showcase, private mode (customize), public mode (search/filter).

Both are generated locally and opened in the user's default browser. No server needed — output is self-contained HTML files.

## Pre-requisite

All work described in this plan assumes the `experimental-llamacpp-v3` branch has been merged into `development`. This means:

- `src/artifactminer/resume/` has the full pipeline source (pipeline.py, models.py, extractors/, queries/, analysis/)
- The OpenTUI screens are wired in `opentui-react-exp/src/index.tsx`
- The local LLM runtime (`src/artifactminer/local_llm/runtime/`) is integrated
- All `/local-llm/*` API routes are functional

---

## System Architecture

```
User runs TUI ─► Uploads ZIP ─► Backend analyzes repos ─► Data in SQLite
                                                              │
                                                    HTML Generator reads DB
                                                              │
                                                    resume.html + portfolio.html
                                                              │
                                                    Opens in default browser
```

---

## New Package: `src/artifactminer/generators/`

```
src/artifactminer/generators/
├── __init__.py
├── resume_html.py          # Collects data + renders resume template
├── portfolio_html.py       # Collects data + renders portfolio template
├── models.py               # Shared data models (ExpertiseLevel, EducationEntry, etc.)
└── templates/
    ├── resume.html          # Jinja2 template — one-page printable resume
    └── portfolio.html       # Jinja2 template — interactive portfolio dashboard
```

### New API Router: `src/artifactminer/api/generate.py`

| Endpoint                  | Method | Request Body                  | Response                              |
|---------------------------|--------|-------------------------------|---------------------------------------|
| `POST /generate/resume`   | POST   | `{ "portfolio_id": "..." }`   | `{ "path": "~/.artifactminer/output/resume.html" }` |
| `POST /generate/portfolio` | POST  | `{ "portfolio_id": "..." }`   | `{ "path": "~/.artifactminer/output/portfolio.html" }` |

Register in `app.py` as `generate_router` from `.generate`.

### New Dependency

Add `jinja2` to `pyproject.toml` dependencies.

### Output Location

`~/.artifactminer/output/` — created automatically if it doesn't exist.

---

## Data Sources Available After Analysis

All data lives in SQLite via SQLAlchemy. Access it via a `Session` from `src/artifactminer/db/database.py` (`get_db()`).

### Skills

**Tables:** `skills`, `project_skills`, `user_project_skills`

| Column              | Type   | Description                                    |
|---------------------|--------|------------------------------------------------|
| `Skill.name`        | String | Canonical skill name (e.g., "Python")          |
| `Skill.category`    | String | Category (e.g., "Programming Languages")       |
| `ProjectSkill.proficiency` | Float | 0.0–1.0, per project                    |
| `ProjectSkill.evidence`    | JSON  | Evidence supporting the proficiency      |

**API:** `GET /skills` returns `list[SkillResponse]` (id, name, category, project_count).

**API:** `GET /skills/chronology` returns `list[SkillChronologyItem]` (date, skill, project, proficiency, category), ordered by first_commit date (oldest first).

### Projects

**Tables:** `repo_stats`, `user_repo_stats`

| Column                           | Type     | Description                                     |
|----------------------------------|----------|-------------------------------------------------|
| `RepoStat.project_name`         | String   | Project/repo name                               |
| `RepoStat.languages`            | JSON     | `{"Python": 60, "JavaScript": 40}`              |
| `RepoStat.language_percentages` | JSON     | Same data, percentage form                      |
| `RepoStat.primary_language`     | String   | Dominant language                                |
| `RepoStat.frameworks`           | JSON     | Detected frameworks list                        |
| `RepoStat.total_commits`        | Integer  | Total commits in repo                           |
| `RepoStat.first_commit`         | DateTime | Earliest commit                                 |
| `RepoStat.last_commit`          | DateTime | Most recent commit                              |
| `RepoStat.health_score`         | Float    | 0–100 project health                            |
| `RepoStat.ranking_score`        | Float    | User contribution ranking                       |
| `UserRepoStat.userStatspercentages` | Float | User's contribution %                        |
| `UserRepoStat.commitFrequency`  | Float    | Commit frequency metric                         |
| `UserRepoStat.activity_breakdown` | JSON   | `{"code": 70, "test": 15, "docs": 10, "config": 5}` |
| `UserRepoStat.user_role`        | String   | Detected role (e.g., "primary contributor")     |

**API:** `GET /projects` returns `list[ProjectResponse]`.
**API:** `GET /projects/{id}` returns `ProjectDetailResponse` (includes skills, resume_items, evidence).
**API:** `GET /projects/ranking` returns `list[ProjectRankingItem]`.

### Resume Items

**Table:** `resume_items`

| Column                | Type   | Description                         |
|-----------------------|--------|-------------------------------------|
| `ResumeItem.title`    | String | Bullet title                        |
| `ResumeItem.content`  | Text   | Bullet content                      |
| `ResumeItem.category` | String | Category (technical, leadership...) |
| `ResumeItem.repo_stat_id` | FK | Links to project                |

**API:** `GET /resume` returns `list[ResumeItemResponse]` (includes `project_name`, `role`).

### Evidence

**Table:** `project_evidence`

| Column                     | Type   | Description                               |
|----------------------------|--------|-------------------------------------------|
| `ProjectEvidence.type`     | String | metric, feedback, award, code_quality, test_coverage, etc. |
| `ProjectEvidence.content`  | Text   | Evidence description                      |
| `ProjectEvidence.source`   | String | Where it came from                        |
| `ProjectEvidence.date`     | Date   | When it occurred                          |

**API:** `GET /projects/{id}/evidence` returns `list[EvidenceResponse]`.

### AI Summaries

**Table:** `user_intelligence_summaries`

| Column                              | Type   | Description              |
|-------------------------------------|--------|--------------------------|
| `UserAIntelligenceSummary.summary_text` | Text | AI-generated summary |
| `UserAIntelligenceSummary.repo_path`    | String | Associated repo path |
| `UserAIntelligenceSummary.user_email`   | String | User's email         |

**API:** `GET /summaries?user_email=X` returns `list[SummaryResponse]`.

### Portfolio

**API:** `POST /portfolio/generate` with `{"portfolio_id": "..."}` returns `PortfolioGenerationResponse` — a combined payload containing projects, resume_items, summaries, skills_chronology, and preferences. This is the richest single endpoint and the primary data source for HTML generation.

---

## Proficiency-to-Level Mapping (Shared Utility)

This mapping is used by both the resume and portfolio generators. Implement in `src/artifactminer/generators/models.py`.

```python
from enum import Enum

class ExpertiseLevel(str, Enum):
    EXPERT = "Expert"
    ADVANCED = "Advanced"
    INTERMEDIATE = "Intermediate"
    BEGINNER = "Beginner"

def proficiency_to_level(proficiency: float | None) -> ExpertiseLevel:
    """Map a 0.0–1.0 proficiency float to a named expertise level."""
    if proficiency is None or proficiency < 0.25:
        return ExpertiseLevel.BEGINNER
    elif proficiency < 0.50:
        return ExpertiseLevel.INTERMEDIATE
    elif proficiency < 0.75:
        return ExpertiseLevel.ADVANCED
    else:
        return ExpertiseLevel.EXPERT
```

When aggregating proficiency across multiple projects for a single skill, use `max()` of all `ProjectSkill.proficiency` values for that skill.

---

## Education & Awards (User-Provided Data)

Education and awards **cannot** be auto-extracted from git repos. The user provides this data, which is stored in new database tables and accessed via new API endpoints.

### Database Models (add to `src/artifactminer/db/models.py`)

```python
class Education(Base):
    __tablename__ = "education"
    id = Column(Integer, primary_key=True)
    institution = Column(String, nullable=False)       # e.g., "University of Florida"
    degree = Column(String, nullable=False)             # e.g., "B.S. Computer Science"
    field_of_study = Column(String, nullable=True)      # e.g., "Computer Science"
    start_date = Column(String, nullable=True)          # e.g., "2020-08"
    end_date = Column(String, nullable=True)            # e.g., "2024-05"
    gpa = Column(String, nullable=True)                 # e.g., "3.8/4.0"
    honors = Column(String, nullable=True)              # e.g., "Cum Laude"
    created_at = Column(DateTime, default=datetime.utcnow)

class Award(Base):
    __tablename__ = "awards"
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)              # e.g., "Dean's List"
    issuer = Column(String, nullable=True)              # e.g., "University of Florida"
    date = Column(String, nullable=True)                # e.g., "2023-05"
    description = Column(String, nullable=True)         # e.g., "Awarded for academic excellence"
    created_at = Column(DateTime, default=datetime.utcnow)
```

### API Endpoints (new router: `src/artifactminer/api/education.py`)

| Endpoint                   | Method | Description                      |
|----------------------------|--------|----------------------------------|
| `GET /education`           | GET    | List all education entries       |
| `POST /education`          | POST   | Create a new education entry     |
| `PUT /education/{id}`      | PUT    | Update an education entry        |
| `DELETE /education/{id}`   | DELETE | Delete an education entry        |
| `GET /awards`              | GET    | List all awards                  |
| `POST /awards`             | POST   | Create a new award               |
| `PUT /awards/{id}`         | PUT    | Update an award                  |
| `DELETE /awards/{id}`      | DELETE | Delete an award                  |

Register in `app.py` as `education_router` from `.education`.

### Alembic Migration

Create a new migration for the `education` and `awards` tables. Use the existing Alembic setup:
```bash
cd src/artifactminer && uv run alembic revision --autogenerate -m "add education and awards tables"
uv run alembic upgrade head
```

---

## Daily Commit Aggregation (for Activity Heatmap)

The portfolio heatmap requires per-day commit counts. This data is computed during analysis and stored for later retrieval.

### Where to Add

Extend `getUserRepoStats()` in `src/artifactminer/RepositoryIntelligence/repo_intelligence_user.py`. After computing the existing user stats, also compute daily commit counts.

### Computation Logic

```python
def get_daily_commit_counts(repo_path: str, user_email: str) -> dict[str, int]:
    """Return {date_string: commit_count} for the user in this repo.

    Example: {"2024-01-15": 3, "2024-01-16": 1, "2024-01-20": 5}
    """
    # Use: git log --author="email" --format="%Y-%m-%d" | sort | uniq -c
    # Or use gitpython/subprocess to iterate commits and count by date
```

### Storage

Add a `daily_commits` column (JSON) to `UserRepoStat`:
```python
daily_commits = Column(JSON, nullable=True)  # {"2024-01-15": 3, ...}
```

### API

Add to the retrieval router (`src/artifactminer/api/retrieval.py`):

| Endpoint                              | Method | Description                                       |
|---------------------------------------|--------|---------------------------------------------------|
| `GET /activity/heatmap?user_email=X`  | GET    | Aggregated daily commits across all user's repos   |

The response merges daily counts from all `UserRepoStat` rows for the user, summing counts for the same date across repos.

### Alembic Migration

Add `daily_commits` column to `user_repo_stats` table.

---

## HTML Output Conventions

All generated HTML files must follow these rules:

1. **Self-contained** — All CSS inline in `<style>` tags. JS either inline or via CDN (Chart.js, cal-heatmap). No local asset files.
2. **Opens with `file://`** — No server required. Use relative paths or CDN URLs only.
3. **Responsive** — Works on desktop and mobile. Use CSS media queries.
4. **Print-friendly (resume only)** — `@media print` CSS that hides navigation, enforces one-page layout, adjusts fonts.
5. **Professional design** — Clean typography, consistent spacing, muted color palette. Reference: modern resume templates and GitHub-style dashboards.
6. **Data embedding** — Inject data as a `<script>const DATA = {...}</script>` block in the HTML. The Jinja2 template reads Python objects and serializes them to JSON.

### Output Directory

```
~/.artifactminer/output/
├── resume.html          # One-page resume
└── portfolio.html       # Interactive portfolio dashboard
```

Created by the generator if it doesn't exist.

---

## Existing Code Patterns to Follow

### API Router Pattern

```python
# src/artifactminer/api/example.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..db.database import get_db

router = APIRouter()

@router.get("/example")
def get_example(db: Session = Depends(get_db)):
    ...
```

Register in `app.py`:
```python
from .example import router as example_router
app.include_router(example_router)
```

### Test Pattern

```python
# tests/api/test_example.py
import pytest
from fastapi.testclient import TestClient
from artifactminer.api.app import create_app

@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)

def test_example_endpoint(client):
    response = client.get("/example")
    assert response.status_code == 200
```

### Alembic Migration Pattern

The app runs `alembic upgrade head` on startup in `create_app()`. New migrations auto-apply.

```bash
cd src/artifactminer
uv run alembic revision --autogenerate -m "description"
```

---

## Testing Conventions

- **Backend tests:** `uv run pytest tests/path/to/test_file.py`
- **Frontend tests:** `cd opentui-react-exp && bun test`
- Use `pytest` fixtures for DB sessions (see existing tests in `tests/api/`)
- Mock external dependencies (git subprocess calls, LLM calls) with `unittest.mock`
- Each new module needs at least:
  - Unit tests for core logic
  - API integration tests for new endpoints
  - Template rendering tests (assert key sections present in output HTML)

---

## Issue Dependency Graph

```
Issue 1: Education/Awards ──────────────┐
                                        ├──► Issue 3: HTML Resume Generator
Issue 2: Proficiency Mapping ───────────┤
                                        ├──► Issue 4: HTML Portfolio Generator
Issue 5: Daily Commit Aggregation ──────┘
```

Issues 1, 2, and 5 can be implemented in parallel (no interdependencies).
Issues 3 and 4 consume outputs from 1, 2, and 5, but should handle missing data gracefully (e.g., "No education entries added" placeholder if Issue 1 isn't done yet).
