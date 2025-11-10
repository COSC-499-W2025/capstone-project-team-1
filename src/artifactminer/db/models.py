from sqlalchemy import Column, Integer, Float, String, DateTime, Boolean, JSON,ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class Artifact(Base):#basic model for artifacts, this will be used to store artifact information in the database
    __tablename__ = "artifacts"

    id = Column(Integer, primary_key=True, index=True)#unique identifier for each artifact
    name = Column(String)#name of the artifact
    path = Column(String, unique=True)#file system path to the artifact
    type = Column(String)#type of the artifact like file or directory
    scanned_at = Column(DateTime, default=datetime.utcnow) #timestamp when the artifact was scanned

class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    # Stable identifier for the question (e.g., "email", "end_goal").
    # New deployments will create this as a column; existing DBs will be migrated at app startup.
    key = Column(String, unique=True, index=True, nullable=True)
    question_text = Column(String, nullable=False)
    order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    # Basic validation/UX metadata
    required = Column(Boolean, default=True)
    answer_type = Column(String, default="text")  # e.g., "text", "email", "choice"

    # Relationship to answers
    answers = relationship("UserAnswer", back_populates="question")


class Consent(Base):
    __tablename__ = "consents"

    id = Column(Integer, primary_key=True, index=True)
    consent_level = Column(String, default="none", nullable=False)
    accepted_at = Column(DateTime, nullable=True)

class RepoStat(Base):#model for storing repository statistics
    __tablename__ = "repo_stats"

    id = Column(Integer, primary_key=True, index=True)
    project_name = Column(String, nullable=False)
    is_collaborative = Column(Boolean, default=False)
    languages = Column(JSON, nullable=True)#list of languages used in the repo
    language_percentages = Column(JSON, nullable=True)#percentage of each language used
    primary_language = Column(String, nullable=True)#primary language of the repo
    first_commit = Column(DateTime, nullable=True)
    last_commit = Column(DateTime, nullable=True)
    total_commits = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class UserRepoStat(Base):#model for storing user-specific repository statistics by project_name: str first_commit,last_commit,total_commits,userStatspercentages, and commitFrequency
    __tablename__ = "user_repo_stats"

    id = Column(Integer, primary_key=True, index=True)
    project_name = Column(String, nullable=False)
    first_commit = Column(DateTime, nullable=True)
    last_commit = Column(DateTime, nullable=True)
    total_commits = Column(Integer, nullable=True)
    userStatspercentages = Column(Float, nullable=True) # Percentage of user's contributions compared to total repo activity
    commitFrequency = Column(Float, nullable=True) # Average number of commits per week by the user
    created_at = Column(DateTime, default=datetime.utcnow)

class UserAIntelligenceSummary(Base):
    __tablename__ = "user_intelligence_summaries"

    id = Column(Integer, primary_key=True, index=True)
    repo_path = Column(String, nullable=False)
    user_email = Column(String, nullable=False)
    summary_text = Column(Text, nullable=False)
    generated_at = Column(DateTime, default=datetime.utcnow)

class UserAnswer(Base):
    """Store user responses to configuration questions.

    Each user answer is linked to a specific question via question_id.
    Question IDs map to specific configuration fields:
        - question_id=1: User email address
        - question_id=2: Artifacts focus (what files to analyze)
        - question_id=3: End goal of analysis
        - question_id=4: Repository priority (git vs all files)
        - question_id=5: File patterns to include/exclude

    Example query to get user's email:
        email_answer = db.query(UserAnswer).filter(
            UserAnswer.question_id == 1
        ).first()
        user_email = email_answer.answer_text if email_answer else None

    Example query to get all user config:
        answers = db.query(UserAnswer).order_by(UserAnswer.question_id).all()
        config = {ans.question_id: ans.answer_text for ans in answers}
    """
    __tablename__ = "user_answers"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    answer_text = Column(Text, nullable=False)
    answered_at = Column(DateTime, default=datetime.utcnow)

    # Relationship to question
    question = relationship("Question", back_populates="answers")

class UploadedZip(Base):
    """Store uploaded ZIP files for artifact analysis.

    Each uploaded ZIP is saved to the filesystem and tracked in the database
    with metadata for later processing.

    Example usage:
        uploaded_zip = UploadedZip(
            filename="portfolio.zip",
            path="./uploads/20251106_142530_portfolio.zip"
        )
        db.add(uploaded_zip)
        db.commit()
    """
    __tablename__ = "uploaded_zips"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)  # Original filename
    path = Column(String, nullable=False)  # Server filesystem path
    uploaded_at = Column(DateTime, default=datetime.utcnow)
