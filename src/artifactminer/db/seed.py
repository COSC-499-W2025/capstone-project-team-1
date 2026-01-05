"""Database seeding functions."""

from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from .models import Question, RepoStat
from ..helpers.time import utcnow


def seed_questions(db: Session) -> None:
    """Populate initial questions if the table is empty."""
    existing_count = db.query(Question).count()
    if existing_count > 0:
        return
    
    questions = [
        Question(
            key="email",
            question_text=(
                "What is your email address? (This helps us identify you in collaborative GitHub projects)"
            ),
            order=1,
            is_active=True,
            required=True,
            answer_type="email",
        ),
        Question(
            key="artifacts_focus",
            question_text=(
                "What artifacts should we focus on? (e.g., code files, documentation, configs)"
            ),
            order=2,
            is_active=True,
            required=True,
            answer_type="text",
        ),
        Question(
            key="end_goal",
            question_text="What is your end goal with this analysis?",
            order=3,
            is_active=True,
            required=True,
            answer_type="text",
        ),
        Question(
            key="repository_priority",
            question_text="Should we prioritize git repository analysis or scan all file types?",
            order=4,
            is_active=True,
            required=True,
            answer_type="text",
        ),
        Question(
            key="file_patterns_include",
            question_text="File names to include. Please separate with commas.",
            order=5,
            is_active=True,
            required=False,
            answer_type="comma_separated",
        ),
        Question(
            key="file_patterns_exclude",
            question_text="File names to exclude. Please separate with commas.",
            order=6,
            is_active=True,
            required=False,
            answer_type="comma_separated",
        ),
    ]
    
    db.add_all(questions)
    db.commit()


def seed_repo_stats(db: Session) -> None:
    """Populate sample repository stats to support timeline features."""

    existing_count = db.query(RepoStat).count()
    if existing_count > 0:
        return

    now = utcnow()

    sample_stats = [
        RepoStat(
            project_name="Platform Core Services",
            project_path="/mock/platform-core-services",
            is_collaborative=True,
            primary_language="Python",
            languages=["Python", "YAML"],
            language_percentages=[70.0, 30.0],
            first_commit=datetime(2018, 7, 1),
            last_commit=now - timedelta(days=5),
            total_commits=1860,
            frameworks=["FastAPI"],
        ),
        RepoStat(
            project_name="Legacy Data Pipeline",
            project_path="/mock/legacy-data-pipeline",
            is_collaborative=False,
            primary_language="Java",
            languages=["Java", "SQL"],
            language_percentages=[80.0, 20.0],
            first_commit=datetime(2020, 2, 10),
            last_commit=datetime(2020, 9, 25),
            total_commits=240,
            frameworks=["Spring"],
        ),
        RepoStat(
            project_name="Analytics Dashboard",
            project_path="/mock/analytics-dashboard",
            is_collaborative=True,
            primary_language="TypeScript",
            languages=["TypeScript", "Python"],
            language_percentages=[65.0, 35.0],
            first_commit=now - timedelta(days=400),
            last_commit=now - timedelta(days=190),
            total_commits=520,
            frameworks=["React", "FastAPI"],
        ),
        RepoStat(
            project_name="Mobile Experience",
            project_path="/mock/mobile-experience",
            is_collaborative=True,
            primary_language="Kotlin",
            languages=["Kotlin", "Swift"],
            language_percentages=[55.0, 45.0],
            first_commit=now - timedelta(days=60),
            last_commit=now - timedelta(days=2),
            total_commits=310,
            frameworks=["Jetpack Compose"],
        ),
    ]

    db.add_all(sample_stats)
    db.commit()


## Note: we intentionally do not include runtime migrations here. Developers should
## delete their existing local DB when schema changes land so the seed can run.
