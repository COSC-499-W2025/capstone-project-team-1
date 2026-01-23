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
        
        print(f"\n{'='*80}")
        print(f"ANALYSIS COMPLETE: {len(analyze_result.repos_analyzed)} repositories analyzed")
        print(f"{'='*80}\n")
        
        # Display detailed insights for each analyzed project
        for idx, repo in enumerate(analyze_result.repos_analyzed, 1):
            print(f"\n{'-'*80}")
            print(f"[{idx}] {repo.project_name}")
            print(f"{'-'*80}")
            print(f"  Path: {repo.project_path}")
            
            if repo.error:
                print(f"  ⚠ Error: {repo.error}")
                continue
            
            # Languages and Frameworks
            if repo.languages:
                print(f"  Languages: {', '.join(repo.languages)}")
            if repo.frameworks:
                print(f"  Frameworks: {', '.join(repo.frameworks)}")
            
            # Skills and Insights
            print(f"  Skills extracted: {repo.skills_count}")
            print(f"  Insights generated: {repo.insights_count}")
            
            # User Contribution Metrics
            if repo.user_contribution_pct is not None:
                print(f"  User contribution: {repo.user_contribution_pct:.1f}%")
            if repo.user_total_commits is not None:
                print(f"  User commits: {repo.user_total_commits}")
            if repo.user_commit_frequency is not None:
                print(f"  Commit frequency: {repo.user_commit_frequency:.2f} commits/week")
            
            # Timeline
            if repo.user_first_commit and repo.user_last_commit:
                first = repo.user_first_commit.strftime("%Y-%m-%d")
                last = repo.user_last_commit.strftime("%Y-%m-%d")
                print(f"  Activity period: {first} → {last}")
        
        print(f"\n{'='*80}\n")
        
        # Retrieve results from database - only for projects analyzed in this ZIP
        print("\nFetching results from analyzed projects...")
        from artifactminer.db.models import ResumeItem, UserAIntelligenceSummary, RepoStat
        from sqlalchemy import or_
        
        # Get the extraction path for this specific ZIP to avoid duplicates
        extraction_path_str = str(uploaded_zip.extraction_path) if uploaded_zip.extraction_path else str(analyze_result.extraction_path)
        
        # Get resume items - only for repos in this specific extraction path
        resume_items_query = db.query(ResumeItem, RepoStat).join(
            RepoStat, ResumeItem.repo_stat_id == RepoStat.id
        ).filter(
            RepoStat.deleted_at.is_(None),
            RepoStat.project_path.like(f"{extraction_path_str}%")
        )
        
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
        
        # Get summaries - only for projects in this specific extraction path
        summaries_query = db.query(UserAIntelligenceSummary).filter(
            UserAIntelligenceSummary.user_email == user_email,
            UserAIntelligenceSummary.repo_path.like(f"{extraction_path_str}%")
        )
        
        summaries = [
            {
                "repo_path": s.repo_path,
                "summary_text": s.summary_text
            }
            for s in summaries_query.all()
        ]
        
        # Build a lookup for summaries by project path
        summary_by_path = {s["repo_path"]: s["summary_text"] for s in summaries}
        
        # Convert analyze_result.repos_analyzed to dict format for export
        project_analyses = [
            {
                "project_name": repo.project_name,
                "project_path": repo.project_path,
                "languages": repo.languages,
                "frameworks": repo.frameworks,
                "skills_count": repo.skills_count,
                "insights_count": repo.insights_count,
                "user_contribution_pct": repo.user_contribution_pct,
                "user_total_commits": repo.user_total_commits,
                "user_commit_frequency": repo.user_commit_frequency,
                "user_first_commit": repo.user_first_commit,
                "user_last_commit": repo.user_last_commit,
                "summary": summary_by_path.get(repo.project_path),
                "error": repo.error if hasattr(repo, 'error') else None,
            }
            for repo in analyze_result.repos_analyzed
        ]
        
        # Export based on file extension
        print(f"Exporting to: {output_path}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if output_path.suffix == ".json":
            result_path = export_to_json(resume_items, summaries, output_path.parent, project_analyses)
        else:  # default to text
            result_path = export_to_text(resume_items, summaries, output_path.parent, project_analyses)
        
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
