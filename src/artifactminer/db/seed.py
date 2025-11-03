"""Database seeding functions."""

from sqlalchemy.orm import Session
from .models import Question


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
            key="file_patterns",
            question_text="Any specific file patterns to include or exclude?",
            order=5,
            is_active=True,
            required=True,
            answer_type="text",
        ),
    ]
    
    db.add_all(questions)
    db.commit()


## Note: we intentionally do not include runtime migrations here. Developers should
## delete their existing local DB when schema changes land so the seed can run.
