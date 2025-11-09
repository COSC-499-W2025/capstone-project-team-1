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
    # Set consent to 'full'
    consent = Consent(consent_level='full')
    db.add(consent)
    db.commit()

    assert user_allows_llm() is True
    db.close()

