# Milestone 3: Resume & Portfolio HTML Generation

## Goal

Generate two HTML deliverables from analyzed project data:

1. **One-page resume** — printable to PDF via browser print. Sections: Education/Awards, Skills by expertise level, Projects with contribution evidence.
2. **Interactive web portfolio** — opens in browser. Features: skills timeline, activity heatmap, top 3 project showcase, private mode (customize), public mode (search/filter).

Both are generated locally and opened in the user's default browser. No server needed — output is self-contained HTML files.

## Pre-requisite

All work described in this plan assumes the `experimental-llamacpp-v3` branch has been merged into `development`. This means:

- `src/artifactminer/resume/` has the full pipeline source
- The OpenTUI screens are wired in `opentui-react-exp/src/index.tsx`
- The local LLM runtime is integrated
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
├── models.py               # Shared models (ExpertiseLevel enum, proficiency mapping)
└── templates/
    ├── resume.html          # Jinja2 — one-page printable resume
    └── portfolio.html       # Jinja2 — interactive portfolio dashboard
```

### New API Router: `src/artifactminer/api/generate.py`

| Endpoint                   | Method | Input           | Output            |
|----------------------------|--------|-----------------|-------------------|
| `POST /generate/resume`    | POST   | `portfolio_id`  | `{ path: "..." }` |
| `POST /generate/portfolio` | POST   | `portfolio_id`  | `{ path: "..." }` |

Register in `app.py`. Add `jinja2` to `pyproject.toml`.

### Output Location

`~/.artifactminer/output/` — auto-created. Files: `resume.html`, `portfolio.html`.

---

## Data Sources

All data lives in SQLite via SQLAlchemy. Access via `get_db()` from `src/artifactminer/db/database.py`.

### Skills

**Tables:** `skills`, `project_skills`, `user_project_skills`

Key fields: `Skill.name`, `Skill.category`, `ProjectSkill.proficiency` (float 0–1), `ProjectSkill.evidence` (JSON).

**APIs:** `GET /skills` (list with category + project_count), `GET /skills/chronology` (timeline ordered by first_commit).

### Projects

**Tables:** `repo_stats`, `user_repo_stats`

Key fields: `RepoStat.project_name`, `.languages` (JSON), `.frameworks` (JSON), `.total_commits`, `.first_commit`, `.last_commit`, `.health_score`, `.ranking_score`, `UserRepoStat.userStatspercentages`, `.commitFrequency`, `.activity_breakdown` (JSON), `.user_role`.

**APIs:** `GET /projects`, `GET /projects/{id}` (includes skills, resume_items, evidence), `GET /projects/ranking`.

### Resume Items

**Table:** `resume_items` — `title`, `content`, `category`, `repo_stat_id` (FK to project).

**API:** `GET /resume` (includes `project_name`, `role`).

### Evidence

**Table:** `project_evidence` — `type` (metric/feedback/award/code_quality/test_coverage/etc.), `content`, `source`, `date`.

**API:** `GET /projects/{id}/evidence`.

### AI Summaries

**Table:** `user_intelligence_summaries` — `summary_text`, `repo_path`, `user_email`.

**API:** `GET /summaries?user_email=X`.

### Portfolio (combined endpoint)

**API:** `POST /portfolio/generate` returns `PortfolioGenerationResponse` — combined payload with projects, resume_items, summaries, skills_chronology, and preferences. Richest single data source.

---

## Proficiency-to-Level Mapping

Shared utility in `src/artifactminer/generators/models.py`. Used by both resume and portfolio generators.

| Proficiency Range | Level        |
|-------------------|--------------|
| ≥ 0.75            | Expert       |
| ≥ 0.50            | Advanced     |
| ≥ 0.25            | Intermediate |
| < 0.25 or None    | Beginner     |

When aggregating across projects for a single skill, use `max()` of all proficiency values.

---

## Education & Awards

Cannot be auto-extracted from git. Users provide this data via TUI screen. Stored in `education` and `awards` DB tables.

### Education fields
`institution` (required), `degree` (required), `field_of_study`, `start_date`, `end_date`, `gpa`, `honors`

### Award fields
`title` (required), `issuer`, `date`, `description`

### API: `src/artifactminer/api/education.py`

Full CRUD (GET/POST/PUT/DELETE) for both `/education` and `/awards`. Register in `app.py`.

---

## Daily Commit Aggregation

Portfolio heatmap needs per-day commit counts. Not currently computed.

- **Compute:** `git log --author=email --format=%Y-%m-%d`, count per date.
- **Store:** New `daily_commits` JSON column on `UserRepoStat` (e.g., `{"2024-01-15": 3}`).
- **Wire:** Call during `POST /analyze/{zip_id}` alongside existing `getUserRepoStats()`.
- **Expose:** `GET /activity/heatmap?user_email=X` — aggregates daily_commits across all repos, sums same-date counts.
- **Migration:** Alembic for the new column.

---

## HTML Output Conventions

1. **Self-contained** — CSS in `<style>`, JS inline or via CDN. No local asset files.
2. **Opens with `file://`** — no server required.
3. **Responsive** — CSS media queries for desktop/mobile.
4. **Print-friendly (resume)** — `@media print` for one-page layout.
5. **Data embedding** — Inject as `<script>const DATA = {...}</script>` in the template.

---

## Conventions

- **API pattern:** See any existing router (e.g., `api/projects.py`) for FastAPI + SQLAlchemy pattern.
- **Test pattern:** See `tests/api/` for TestClient fixture usage.
- **Alembic:** App runs `upgrade head` on startup. Generate with `uv run alembic revision --autogenerate -m "..."` from `src/artifactminer/`.
- **Backend tests:** `uv run pytest tests/path/to/test.py`
- **Frontend tests:** `cd opentui-react-exp && bun test`

---

## Issue Dependency Graph

```
#508 Education/Awards ──────────────┐
                                    ├──► #510 HTML Resume Generator
#509 Proficiency Mapping ───────────┤
                                    ├──► #511 HTML Portfolio Generator
#512 Daily Commit Aggregation ──────┘
```

#508, #509, #512 can be implemented in parallel.
#510 and #511 consume their outputs but should handle missing data gracefully.
