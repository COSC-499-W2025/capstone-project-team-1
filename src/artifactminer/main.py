"""ArtifactMiner CLI for non-interactive portfolio analysis."""

import argparse
import sys
import shutil
import asyncio
from pathlib import Path
from datetime import datetime, UTC
from sqlalchemy.orm import Session

from artifactminer.db import SessionLocal, UploadedZip, Consent, Question, UserAnswer
from artifactminer.api.zip import UPLOADS_DIR
from artifactminer.api.analyze import extract_zip_to_persistent_location, router
from artifactminer.tui.helpers import export_to_json, export_to_text


def setup_consent(db: Session, level: str) -> None:
    """Set consent level in database."""
    consent = db.get(Consent, 1)
    if consent is None:
        consent = Consent(id=1, consent_level=level, accepted_at=datetime.now(UTC))
        db.add(consent)
    else:
        consent.consent_level = level
        if level in ("full", "no_llm"):
            consent.accepted_at = datetime.now(UTC)
    db.commit()


def setup_user_email(db: Session, email: str) -> None:
    """Set user email in database."""
    email_question = db.query(Question).filter(Question.key == "email").first()
    if not email_question:
        # Create email question if it doesn't exist
        email_question = Question(
            key="email",
            text="What is your email?",
            order=1
        )
        db.add(email_question)
        db.commit()
        db.refresh(email_question)
    
    # Delete existing answer and add new one
    db.query(UserAnswer).filter(UserAnswer.question_id == email_question.id).delete()
    answer = UserAnswer(
        question_id=email_question.id,
        answer_text=email,
        answered_at=datetime.now(UTC)
    )
    db.add(answer)
    db.commit()


async def run_analysis(input_path: Path, output_path: Path, consent_level: str, user_email: str) -> None:
    """Run non-interactive analysis pipeline."""
    db = SessionLocal()
    
    try:
        # Setup consent and user email
        print(f"Setting consent level: {consent_level}")
        setup_consent(db, consent_level)
        
        print(f"Setting user email: {user_email}")
        setup_user_email(db, user_email)
        
        # Upload ZIP
        print(f"Uploading ZIP: {input_path}")
        UPLOADS_DIR.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{timestamp}_{input_path.name}"
        dest_path = UPLOADS_DIR / safe_filename
        
        shutil.copy2(input_path, dest_path)
        
        uploaded_zip = UploadedZip(
            filename=input_path.name,
            path=str(dest_path),
            portfolio_id="cli-generated"
        )
        db.add(uploaded_zip)
        db.commit()
        db.refresh(uploaded_zip)
        
        # Extract and analyze using the API router function
        print(f"Extracting and analyzing ZIP (ID: {uploaded_zip.id})...")
        
        # Call the async analyze_zip function directly
        from artifactminer.api.analyze import analyze_zip
        from artifactminer.api.schemas import AnalyzeRequest
        
        analyze_result = await analyze_zip(
            zip_id=uploaded_zip.id,
            request=None,  # Auto-discover all repos
            db=db
        )
        
        print(f"Analyzed {len(analyze_result.repos_analyzed)} repositories")
        
        # Retrieve results from database
        print("Fetching results...")
        from artifactminer.db.models import ResumeItem, UserAIntelligenceSummary, RepoStat
        from sqlalchemy import or_
        
        # Get resume items
        resume_items_query = db.query(ResumeItem, RepoStat).outerjoin(
            RepoStat, ResumeItem.repo_stat_id == RepoStat.id
        ).filter(or_(RepoStat.deleted_at.is_(None), RepoStat.id.is_(None)))
        
        resume_items = [
            {
                "id": item.id,
                "title": item.title,
                "content": item.content,
                "category": item.category,
                "project_name": repo.project_name if repo else None
            }
            for item, repo in resume_items_query.all()
        ]
        
        # Get summaries
        summaries_query = db.query(UserAIntelligenceSummary).filter(
            UserAIntelligenceSummary.user_email == user_email
        )
        
        summaries = [
            {
                "repo_path": s.repo_path,
                "summary_text": s.summary_text
            }
            for s in summaries_query.all()
        ]
        
        # Export based on file extension
        print(f"Exporting to: {output_path}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if output_path.suffix == ".json":
            result_path = export_to_json(resume_items, summaries, output_path.parent)
        else:  # default to text
            result_path = export_to_text(resume_items, summaries, output_path.parent)
        
        # Rename to user-specified name
        if result_path.exists():
            result_path.rename(output_path)
        
        print(f"✓ Analysis complete! Results saved to: {output_path}")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


def main():
    """CLI entry point for ArtifactMiner."""
    parser = argparse.ArgumentParser(
        prog="artifactminer",
        description="Analyze student project portfolios and generate resumes"
    )
    
    parser.add_argument(
        "-i", "--input",
        type=Path,
        required=True,
        help="Path to input ZIP file"
    )
    
    parser.add_argument(
        "-o", "--output",
        type=Path,
        required=True,
        help="Path to output file (.json or .txt)"
    )
    
    parser.add_argument(
        "-c", "--consent",
        choices=["full", "no_llm", "none"],
        default="no_llm",
        help="Consent level for LLM usage (default: no_llm)"
    )
    
    parser.add_argument(
        "-u", "--user-email",
        default="cli-user@example.com",
        help="User email for analysis tracking (default: cli-user@example.com)"
    )
    
    args = parser.parse_args()
    
    # Validate input
    if not args.input.exists():
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)
    
    if not args.input.suffix == ".zip":
        print(f"Error: Input must be a ZIP file", file=sys.stderr)
        sys.exit(1)
    
    # Run analysis
    asyncio.run(run_analysis(args.input, args.output, args.consent, args.user_email))


if __name__ == "__main__":
    main()
