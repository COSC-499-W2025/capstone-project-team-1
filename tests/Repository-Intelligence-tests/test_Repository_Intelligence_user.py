# Part of the Repository Intelligence Module
# Owner: Evan/van-cpu
# Tests for AI-driven user commit summarization

import sys
import os
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.artifactminer.RepositoryIntelligence.repo_intelligence_user import createSummaryFromUserAdditions, createAIsummaryFromUserAdditions, user_allows_llm, collect_user_additions
from src.artifactminer.db.database import SessionLocal
from src.artifactminer.db.models import Consent


def test_user_allows_llm_default_false():
    db = SessionLocal()
    # Ensure no consent record exists
    db.query(Consent).delete()
    db.commit()

    assert user_allows_llm() is False
    db.close()
def test_user_allows_llm_true():
    db = SessionLocal()
    # Set consent to 'full'
    consent = Consent(consent_level='full')
    db.add(consent)
    db.commit()

    assert user_allows_llm() is True
    db.close()
def testcreateSummaryFromUserAdditions():
    additions = [
        "+ This is the first added line.",
        "+ Another line added by the user.",
        "+ Final addition to the code."
    ]
    summary = createSummaryFromUserAdditions(additions)
    assert summary is not None

def test_createAIsummaryFromUserAdditions():
    root = Path(__file__).resolve().parents[2]
    email = "ecrowl01@student.ubc.ca"
    additions = collect_user_additions(root, email)  # Collect additions first
    summary = createAIsummaryFromUserAdditions(additions)
    assert summary is not None
    print("AI-generated summary:", summary)
