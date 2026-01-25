"""ArtifactMiner CLI for portfolio analysis (interactive and non-interactive)."""

import argparse
import sys
import shutil
import asyncio
from pathlib import Path
from datetime import datetime, UTC
from fastapi import UploadFile
from sqlalchemy.orm import Session

from artifactminer.api.retrieval import get_AI_summaries, get_summaries
from artifactminer.api.schemas import ConsentResponse, UserAnswerCreate, ZipUploadResponse
from artifactminer.db import SessionLocal
from artifactminer.db import Consent, UserAnswer
from artifactminer.db.models import Question
from artifactminer.tui.helpers import export_to_json, export_to_text


async def setup_consent(db: Session, level: str) -> None:
    """Set consent level in database."""
    #API: calling consent async
    from artifactminer.api.consent import update_consent
    db = SessionLocal()
    consent_created = ConsentResponse(consent_level=level, datetime=datetime.now(UTC))
    consent = await update_consent(consent_created, db)
    print("\nconsent response: ", consent.consent_level)


async def setup_user_email(db: Session, email: str) -> None:
    """Set user email in database."""
    #API: calling user answer (email) async
    from artifactminer.api.user_info import create_user_answer 
    db = SessionLocal()
    user_answer_created = UserAnswerCreate(email=email)
    user_answer = await create_user_answer(user_answer_created,db)
    print("\nemail response: ", user_answer.answer_text)



async def upload_zip(input_path:Path) -> ZipUploadResponse:
    #API: calling upload zip async
    from artifactminer.api.zip import upload_zip
  
    db = SessionLocal()
    with open(input_path, "rb") as f:
        upload_file = UploadFile(
            filename=input_path.name,
            file=f,
        )
        upload_zip_payload = await upload_zip(file=upload_file,portfolio_id="cli-generated",db=db)
        upload_zip_payload.json()

    return upload_zip_payload


async def run_analysis(input_path: Path, output_path: Path, consent_level: str, user_email: str) -> None:
    """Run non-interactive analysis pipelixne."""
    from artifactminer.db import SessionLocal
    
    db = SessionLocal()

    upload_payload = await upload_zip(input_path)
    
    try:

        # Setup consent and user email
        print(f"\n{'='*80}")
        print(f"Setting consent level: {consent_level}")
        await setup_consent(db, consent_level)
        
        print(f"Setting user email: {user_email}")
        await setup_user_email(db, user_email)
        print(f"\n{'='*80}")
        # Upload ZIP
        print(f"Uploading ZIP: {input_path}")

        # Extract and analyze using the API router function
        print(f"Extracting and analyzing ZIP (ID: {upload_payload.zip_id})...")
        
        # Call the async analyze_zip function directly
        from artifactminer.api.analyze import analyze_zip
        
        analyze_result = await analyze_zip(
            zip_id=upload_payload.zip_id,
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
                print(f"⚠ Error: {repo.error}")
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
        
        # Get the extraction path for this specific ZIP to avoid duplicates
        extraction_path_str = str(analyze_result.extraction_path) if analyze_result.extraction_path else str(analyze_result.extraction_path)
        
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
        
        #API: CALLS get_summaries async
        summaries_all = await get_AI_summaries(user_email,extraction_path_str, db)
        
        summaries = [
            {
                "repo_path": s.repo_path,
                "summary_text": s.summary_text
            }
            for s in summaries_all
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
        
        # Validate output format
        if output_path.suffix not in (".json", ".txt"):
            print(f"Warning: Unsupported output format '{output_path.suffix}'. Supported formats are .json and .txt. Defaulting to .txt")
            output_path = output_path.with_suffix(".txt")
        
        if output_path.suffix == ".json":
            result_path = export_to_json(resume_items, summaries, output_path.parent, project_analyses)
        else:
            result_path = export_to_text(resume_items, summaries, output_path.parent, project_analyses)
        
        # Move to user-specified name (handles existing files on Windows)
        if result_path.exists():
            shutil.move(str(result_path), str(output_path))
        
        print(f"✓ Analysis complete! Results saved to: {output_path}")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


def print_header() -> None:
    """Print the interactive CLI header."""
    print("\n" + "=" * 60)
    print("                    ARTIFACT MINER")
    print("           Student Portfolio Analysis Tool")
    print("=" * 60 + "\n")


def _strip_wrapping_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def _normalize_path_value(value):
    if value is None:
        return None
    if isinstance(value, Path):
        return value.expanduser().resolve()
    return Path(_strip_wrapping_quotes(str(value))).expanduser().resolve()


def _validate_input_path(path):
    path = _normalize_path_value(path)
    if path is None:
        return None
    if not path.exists():
        print(f"File not found: {path}")
        return None
    if path.suffix.lower() != ".zip":
        print("File must be a .zip archive.")
        return None
    return path


def _confirm_overwrite(path: Path) -> bool:
    while True:
        response = input(f"Output file exists: {path}. Overwrite? [y/N]: ").strip().lower()
        if response in ("y", "yes"):
            return True
        if response in ("", "n", "no"):
            return False
        print("Please enter y or n.")


def _validate_output_path(path, confirm_overwrite: bool = False):
    path = _normalize_path_value(path)
    if path is None:
        return None
    if path.suffix.lower() not in (".json", ".txt"):
        print("Output must be .json or .txt")
        return None
    if confirm_overwrite and path.exists():
        if not _confirm_overwrite(path):
            return None
    return path


def prompt_consent() -> str:
    print("Step 1: Consent")
    print("-" * 40)
    print("Choose your consent level:")
    print("  [1] Full   - Allow LLM processing for enhanced analysis")
    print("  [2] No LLM - Local analysis only (no external AI)")
    print("  [3] None   - Minimal analysis")
    print()

    choices = {"1": "full", "2": "no_llm", "3": "none"}
    while True:
        choice = input("Enter choice [1/2/3] (default: 2): ").strip() or "2"
        if choice in choices:
            print(f"Consent: {choices[choice]}\n")
            return choices[choice]
        print("Invalid choice. Enter 1, 2, or 3.")


def prompt_email() -> str:
    print("Step 2: User Information")
    print("-" * 40)
    while True:
        email = input("Enter your email address: ").strip()
        if "@" in email and "." in email:
            print(f"Email: {email}\n")
            return email
        print("Please enter a valid email address.")


def prompt_input_file(initial=None) -> Path:
    print("Step 3: Input File")
    print("-" * 40)
    if initial is not None:
        validated = _validate_input_path(initial)
        if validated is not None:
            size_mb = validated.stat().st_size / (1024 * 1024)
            print(f"Found: {validated.name} ({size_mb:.1f} MB)\n")
            return validated
    while True:
        path_str = _strip_wrapping_quotes(input("Enter path to ZIP file: "))
        if not path_str:
            print("Please enter a path.")
            continue
        validated = _validate_input_path(path_str)
        if validated is None:
            continue
        size_mb = validated.stat().st_size / (1024 * 1024)
        print(f"Found: {validated.name} ({size_mb:.1f} MB)\n")
        return validated


def prompt_output_file(initial=None) -> Path:
    print("Step 4: Output File")
    print("-" * 40)
    if initial is not None:
        validated = _validate_output_path(initial, confirm_overwrite=True)
        if validated is not None:
            print(f"Output: {validated.name}\n")
            return validated
    while True:
        path_str = _strip_wrapping_quotes(input("Enter output path (.json or .txt): "))
        if not path_str:
            print("Please enter a path.")
            continue
        validated = _validate_output_path(path_str, confirm_overwrite=True)
        if validated is None:
            continue
        print(f"Output: {validated.name}\n")
        return validated


def run_interactive(input_path=None, output_path=None, consent=None, email=None) -> None:
    """Run CLI in interactive mode - collect inputs via prompts, then call run_analysis()."""
    try:
        print_header()

        if consent is None:
            consent = prompt_consent()
        if email is None:
            email = prompt_email()

        input_path = prompt_input_file(input_path)
        output_path = prompt_output_file(output_path)

        print("Proceed with analysis? [Y/n]: ", end="")
        if input().strip().lower() not in ("", "y", "yes"):
            print("Cancelled.")
            sys.exit(0)

        print()
        asyncio.run(run_analysis(input_path, output_path, consent, email))
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled.")
        sys.exit(0)


def main():

    """Adding arguments:"""

    """CLI entry point for ArtifactMiner."""
    parser = argparse.ArgumentParser(
        prog="artifactminer",
        description="Analyze student project portfolios and generate resumes"
    )
    
    parser.add_argument(
        "-i", "--input",
        type=Path,
        help="Path to input ZIP file"
    )
    
    parser.add_argument(
        "-o", "--output",
        type=Path,
        help="Path to output file (.json or .txt)"
    )
    
    parser.add_argument(
        "-c", "--consent",
        choices=["full", "no_llm", "none"],
        default=None,
        help="Consent level for LLM usage (default: no_llm)"
    )
    
    parser.add_argument(
        "-u", "--user-email",
        default=None,
        help="User email for analysis tracking (default: cli-user@example.com)"
    )
    
    args = parser.parse_args()
    
    if args.input and args.output:
        input_path = _validate_input_path(args.input)
        if input_path is None:
            print(f"Error: Invalid input file: {args.input}", file=sys.stderr)
            sys.exit(1)
        consent = args.consent or "no_llm"
        email = args.user_email or "cli-user@example.com"
        asyncio.run(run_analysis(input_path, args.output, consent, email))
    else:
        run_interactive(
            input_path=args.input,
            output_path=args.output,
            consent=args.consent,
            email=args.user_email,
        )


if __name__ == "__main__":
    main()
