# tests/Repository-Intelligence-tests/test_full_pipeline.py

import shutil
import zipfile
from datetime import datetime, UTC
from pathlib import Path

from artifactminer.db.database import SessionLocal
from artifactminer.db.models import (
    UploadedZip,
    RepoStat,
    UserRepoStat,
    UserAIntelligenceSummary,
    UserAnswer
)
from artifactminer.RepositoryIntelligence.repo_intelligence_main import (
    getRepoStats,
    saveRepoStats
)
from artifactminer.RepositoryIntelligence.repo_intelligence_user import (
    getUserRepoStats,
    saveUserRepoStats,
    generate_summaries_for_ranked
)
from artifactminer.helpers.project_ranker import rank_projects
from artifactminer.RepositoryIntelligence.repo_intelligence_AI import set_user_consent
import pytest


@pytest.mark.asyncio
async def test_full_pipeline_zip_to_summaries():
    """
    Full simulation of:
    ZIP → extract → discover repos → analyze → rank → summarize
    """

    extract_dir = None
    # 0. Setup DB session
    db = SessionLocal()

    try:
        # 0a. Clean up old test data to avoid stale paths
        db.query(UserAIntelligenceSummary).delete()
        db.query(UserRepoStat).delete()
        db.query(RepoStat).delete()
        db.query(UploadedZip).delete()
        db.query(UserAnswer).delete()
        db.commit()
        
        set_user_consent("full")  # Disable LLM calls for testing


        # 1. Insert user config (email)
        test_email = "shlok10@student.ubc.ca"
        user_answer = UserAnswer(question_id=1, answer_text=test_email)
        db.add(user_answer)
        db.commit()

        # 2. Insert fake UploadedZip row
        zip_path = Path("tests/data/mock_projects.zip")
        assert zip_path.exists(), "Test zip file missing!"

        uploaded_zip = UploadedZip(
            filename="mock_projects.zip",
            path=str(zip_path)
        )
        db.add(uploaded_zip)
        db.commit()

        # 3. Extract ZIP to test directory
        extract_dir = Path(f"./temp_extract_{uploaded_zip.id}")
        extract_dir.mkdir(exist_ok=True)

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)

        uploaded_zip.extraction_path = str(extract_dir)
        db.commit()

        # 4. Discover git repos
        git_repos = [
            p for p in extract_dir.rglob("*")
            if p.is_dir() and (p / ".git").exists()
        ]

        assert len(git_repos) > 0, "No git repos discovered in extracted zip."

        # 5. Analyze each repo (same logic as `/repos/analyze`)
        for repo in git_repos:
            repo_stats = getRepoStats(str(repo))
            saveRepoStats(repo_stats)

            user_stats = getUserRepoStats(str(repo), test_email)
            saveUserRepoStats(user_stats)

        # 6. Rank repos (using existing helper)
        ranking_results = rank_projects(str(extract_dir), test_email)

        # 7. Persist ranking to RepoStat table
        for ranked in ranking_results:
            repo_stat = db.query(RepoStat).filter(
                RepoStat.project_name == ranked["name"]
            ).first()

            if repo_stat:
                repo_stat.ranking_score = ranked["score"]
                repo_stat.ranked_at = datetime.now(UTC).replace(tzinfo=None)

        db.commit()

        # 8. Generate summaries
        summaries = await generate_summaries_for_ranked(db)

        # 9. Assert summaries created
        assert len(summaries) > 0
        assert len(summaries) <= 3

        # Also verify DB persisted entries
        stored = db.query(UserAIntelligenceSummary).all()
        #print stored summaries as strings for debugging
        print("Stored UserAIntelligenceSummaries:")
        for s in stored:
            print(f"- ID: {s.id}, Repo: {s.repo_path}, Summary: {s.summary_text[:30]}...")
        assert len(stored) > 0

    finally:
        if extract_dir and extract_dir.exists():
            shutil.rmtree(extract_dir, ignore_errors=True)
        db.close()
