# Part of the Repository Intelligence Module
# Owner: Evan/van-cpu
# Tests for AI-driven user commit summarization

import sys
import os
from pathlib import Path
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.artifactminer.RepositoryIntelligence.repo_intelligence_AI import user_allows_llm, createAIsummaryFromUserAdditions, group_additions_into_blocks, set_user_consent
from src.artifactminer.RepositoryIntelligence.repo_intelligence_user import collect_user_additions
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
    consent = db.get(Consent, 1)
    if consent:
        consent.consent_level = "all"
    else:
        consent = Consent(id=1, consent_level="all")
        db.add(consent)
    db.commit()
    db.close()

    assert user_allows_llm() is False


def test_user_allows_llm_false():
    db = SessionLocal()
    consent = db.get(Consent, 1)
    if consent:
        consent.consent_level = "none"
    else:
        consent = Consent(id=1, consent_level="none")
        db.add(consent)
    db.commit()
    db.close()

    assert user_allows_llm() is False

def test_create_AI_summary_example():
    set_user_consent("full")  # Ensure consent is given for LLM usage
    additions = [
        "Fixed bug in user authentication module.",
        "Refactored database connection logic for better performance.",
        "Added unit tests for the payment processing feature."
    ]
    summary0 = createAIsummaryFromUserAdditions(additions) 
    print(f"AI Summary Example: {summary0}")
    assert isinstance(summary0, str)
    assert len(summary0) > 0


def test_user_additions_collection():
    set_user_consent("full")  # Ensure consent is given for LLM usage
    root = Path(__file__).resolve().parents[2]
    # Replace with a valid email present in the commit history of the repo
    test_email = "ecrowl01@student.ubc.ca"
    additions = collect_user_additions(root, test_email, max_commits=100)
    summarized_texts = group_additions_into_blocks(additions, max_blocks=2, max_chars_per_block=10000)
    summary1 = createAIsummaryFromUserAdditions(summarized_texts)
    print(f"Collected {len(additions)} additions, summarized into {len(summarized_texts)} blocks.")
    print(f"AI Summary from User Additions: {summary1}")
    assert isinstance(summary1, str)