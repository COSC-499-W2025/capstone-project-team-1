"""Database seeding functions."""

from sqlalchemy.orm import Session
from .models import Question


def seed_questions(db: Session) -> None:
    """Populate initial questions if the table is empty."""
    existing_count = db.query(Question).count()
    if existing_count > 0:
        return
    
    questions = [
        Question(question_text="What artifacts should we focus on? (e.g., code files, documentation, configs)", order=1, is_active=True),
        Question(question_text="What is your end goal with this analysis?", order=2, is_active=True),
        Question(question_text="Should we prioritize git repository analysis or scan all file types?", order=3, is_active=True),
        Question(question_text="Any specific file patterns to include or exclude?", order=4, is_active=True),
    ]
    
    db.add_all(questions)
    db.commit()
