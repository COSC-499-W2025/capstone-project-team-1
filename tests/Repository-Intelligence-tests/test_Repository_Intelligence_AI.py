# Part of the Repository Intelligence Module
# Owner: Evan/van-cpu
# Tests for AI-driven user commit summarization

import sys
import os
from pathlib import Path
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.artifactminer.RepositoryIntelligence.repo_intelligence_AI import user_allows_llm
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

