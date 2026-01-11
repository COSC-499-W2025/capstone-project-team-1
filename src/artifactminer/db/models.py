from sqlalchemy import Column, Integer, Float, String, DateTime, Boolean, JSON, ForeignKey, Text, UniqueConstraint
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
    consent_level = Column(String, default="none", nullable=False) # e.g., "none", "full"
    LLM_model = Column(String, default="chatGPT", nullable=False) # e.g., "ollama", "chatGPT"
    accepted_at = Column(DateTime, nullable=True)

class RepoStat(Base):#model for storing repository statistics
    __tablename__ = "repo_stats"

    id = Column(Integer, primary_key=True, index=True)
    project_name = Column(String, nullable=False)
    project_path = Column(String, nullable=False)
    is_collaborative = Column(Boolean, default=False)
    languages = Column(JSON, nullable=True)#list of languages used in the repo
    language_percentages = Column(JSON, nullable=True)#percentage of each language used
    primary_language = Column(String, nullable=True)#primary language of the repo
    first_commit = Column(DateTime, nullable=True)
    last_commit = Column(DateTime, nullable=True)
    total_commits = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    frameworks = Column(JSON, nullable=True)
    collaboration_metadata = Column(JSON, nullable=True)
    ranking_score = Column(Float, nullable=True)
    ranked_at = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True)
    health_score = Column(Float, nullable=True)  # Repository health indicator (0-100)

    # Relationships
    project_skills = relationship("ProjectSkill", back_populates="repo_stat", cascade="all, delete-orphan")
    user_project_skills = relationship(
        "UserProjectSkill", back_populates="repo_stat", cascade="all, delete-orphan"
    )
    resume_items = relationship("ResumeItem", back_populates="repo_stat", cascade="all, delete-orphan")

class UserRepoStat(Base):#model for storing user-specific repository statistics by project_name: str first_commit,last_commit,total_commits,userStatspercentages, and commitFrequency
    __tablename__ = "user_repo_stats"

    id = Column(Integer, primary_key=True, index=True)
    project_name = Column(String, nullable=False)
    project_path = Column(String, nullable=False)
    first_commit = Column(DateTime, nullable=True)
    last_commit = Column(DateTime, nullable=True)
    total_commits = Column(Integer, nullable=True)
    userStatspercentages = Column(Float, nullable=True) # Percentage of user's contributions compared to total repo activity
    commitFrequency = Column(Float, nullable=True) # Average number of commits per week by the user
    created_at = Column(DateTime, default=datetime.utcnow)
    activity_breakdown = Column(JSON, nullable=True)

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
    extraction_path = Column(String, nullable=True)


class Skill(Base):
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    category = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    project_skills = relationship("ProjectSkill", back_populates="skill", cascade="all, delete-orphan")
    user_project_skills = relationship("UserProjectSkill", back_populates="skill", cascade="all, delete-orphan")


class ProjectSkill(Base):
    __tablename__ = "project_skills"
    __table_args__ = (
        UniqueConstraint('repo_stat_id', 'skill_id', name='uq_project_skill'),
    )

    id = Column(Integer, primary_key=True, index=True)
    repo_stat_id = Column(Integer, ForeignKey("repo_stats.id", ondelete="CASCADE"), nullable=False)
    skill_id = Column(Integer, ForeignKey("skills.id", ondelete="CASCADE"), nullable=False)
    weight = Column(Float, nullable=True)
    proficiency = Column(Float, nullable=True)
    evidence = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    repo_stat = relationship("RepoStat", back_populates="project_skills")
    skill = relationship("Skill", back_populates="project_skills")


class UserProjectSkill(Base):
    """User-scoped skills for collaborative repositories."""

    __tablename__ = "user_project_skills"
    __table_args__ = (
        UniqueConstraint("repo_stat_id", "skill_id", "user_email", name="uq_user_project_skill"),
    )

    id = Column(Integer, primary_key=True, index=True)
    repo_stat_id = Column(Integer, ForeignKey("repo_stats.id", ondelete="CASCADE"), nullable=False)
    skill_id = Column(Integer, ForeignKey("skills.id", ondelete="CASCADE"), nullable=False)
    user_email = Column(String, nullable=False)
    proficiency = Column(Float, nullable=True)
    evidence = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    repo_stat = relationship("RepoStat", back_populates="user_project_skills")
    skill = relationship("Skill", back_populates="user_project_skills")


class ResumeItem(Base):
    __tablename__ = "resume_items"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String, nullable=True)
    repo_stat_id = Column(Integer, ForeignKey("repo_stats.id", ondelete="CASCADE"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    repo_stat = relationship("RepoStat", back_populates="resume_items")


class Export(Base):
    __tablename__ = "exports"

    id = Column(Integer, primary_key=True, index=True)
    export_type = Column(String, nullable=False)
    path = Column(String, nullable=False)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
