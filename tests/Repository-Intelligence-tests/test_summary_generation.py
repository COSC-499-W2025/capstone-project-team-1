from __future__ import annotations

from datetime import UTC, datetime

import pytest

from artifactminer.RepositoryIntelligence.repo_intelligence_user import (
    generate_summaries_for_ranked,
)
from artifactminer.db.database import SessionLocal
from artifactminer.db.models import (
    RepoStat,
    UserAIntelligenceSummary,
    UserAnswer,
    UserRepoStat,
)


@pytest.mark.asyncio
async def test_generate_summaries_for_ranked_creates_static_summary() -> None:
    db = SessionLocal()
    try:
        db.query(UserAIntelligenceSummary).delete()
        db.query(UserRepoStat).delete()
        db.query(RepoStat).delete()
        db.query(UserAnswer).delete()
        db.commit()

        db.add(UserAnswer(question_id=1, answer_text="test@example.com"))
        repo = RepoStat(
            project_name="alpha",
            project_path="/tmp/alpha",
            languages=["Python", "TypeScript"],
            ranking_score=92.0,
            ranked_at=datetime.now(UTC).replace(tzinfo=None),
        )
        db.add(repo)
        db.flush()
        db.add(
            UserRepoStat(
                project_name="alpha",
                project_path="/tmp/alpha",
                userStatspercentages=67.5,
            )
        )
        db.commit()

        summaries = await generate_summaries_for_ranked(db)

        assert len(summaries) == 1
        assert summaries[0]["project_name"] == "alpha"
        assert summaries[0]["summary"] == (
            "User contributed 67.5% to alpha using Python, TypeScript."
        )

        stored = db.query(UserAIntelligenceSummary).all()
        assert len(stored) == 1
        assert stored[0].summary_text == summaries[0]["summary"]
    finally:
        db.close()


@pytest.mark.asyncio
async def test_generate_summaries_for_ranked_includes_role_when_present() -> None:
    db = SessionLocal()
    try:
        db.query(UserAIntelligenceSummary).delete()
        db.query(UserRepoStat).delete()
        db.query(RepoStat).delete()
        db.query(UserAnswer).delete()
        db.commit()

        db.add(UserAnswer(question_id=1, answer_text="test@example.com"))
        repo = RepoStat(
            project_name="beta",
            project_path="/tmp/beta",
            languages=["Go"],
            ranking_score=88.0,
            ranked_at=datetime.now(UTC).replace(tzinfo=None),
        )
        db.add(repo)
        db.flush()
        db.add(
            UserRepoStat(
                project_name="beta",
                project_path="/tmp/beta",
                userStatspercentages=42.0,
                user_role="Lead Developer",
            )
        )
        db.commit()

        summaries = await generate_summaries_for_ranked(db)

        assert len(summaries) == 1
        assert summaries[0]["summary"] == (
            "User served as Lead Developer on beta and contributed 42.0% using Go."
        )
    finally:
        db.close()
