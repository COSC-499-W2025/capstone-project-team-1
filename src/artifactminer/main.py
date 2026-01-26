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
from artifactminer.db import SessionLocal, Consent, UserAnswer, UploadedZip
from artifactminer.tui.helpers import export_to_json, export_to_text
from artifactminer.api.analyze import discover_git_repos, extract_zip_to_persistent_location
from artifactminer.api.zip import UPLOADS_DIR
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    MofNCompleteColumn,
)
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    MofNCompleteColumn,
)


async def setup_consent(db: Session, level: str) -> None:
    """Set consent level in database."""
    #API: calling consent async
    from artifactminer.api.consent import update_consent
    consent_created = ConsentResponse(consent_level=level, datetime=datetime.now(UTC))
    consent = await update_consent(consent_created, db)
    print("\nconsent response: ", consent.consent_level)


async def setup_user_email(db: Session, email: str) -> None:
    """Set user email in database."""
    #API: calling user answer (email) async
    from artifactminer.api.user_info import create_user_answer 
    user_answer_created = UserAnswerCreate(email=email)
    user_answer = await create_user_answer(user_answer_created,db)
    print("\nemail response: ", user_answer.answer_text)


async def upload_zip(input_path:Path,db) -> ZipUploadResponse:
    #API: calling upload zip async
    from artifactminer.api.zip import upload_zip
  
 
    with open(input_path, "rb") as f:
        upload_file = UploadFile(
            filename=input_path.name,
            file=f,
        )
        upload_zip_payload = await upload_zip(file=upload_file,portfolio_id="cli-generated",db=db)

    return upload_zip_payload


async def run_analysis(
    input_path: Path,
    output_path: Path,
    consent_level: str,
    user_email: str,
    selected_repos: list[Path] | None = None,
    zip_id: int | None = None,
) -> None:
    """Run non-interactive analysis pipeline."""
    from artifactminer.db import SessionLocal
    from artifactminer.api.schemas import AnalyzeRequest

    db = SessionLocal()

    try:
        if zip_id is None:
            upload_payload = await upload_zip(input_path, db)
            active_zip_id = upload_payload.zip_id
            print(f"Uploading ZIP: {input_path}")
        else:
            active_zip_id = zip_id
            print(f"Using existing ZIP (ID: {active_zip_id})")
        
        # Setup consent and user email
        print(f"\n{'='*80}")
        print(f"Setting consent level: {consent_level}")
        await setup_consent(db, consent_level)
        
        print(f"Setting user email: {user_email}")
        await setup_user_email(db, user_email)
        print(f"\n{'='*80}")

        # Extract and analyze using the API router function
        print(f"Extracting and analyzing ZIP (ID: {active_zip_id})...")
        
        # Call the async analyze_zip function directly
        from artifactminer.api.analyze import analyze_zip
        
        request = None
        if selected_repos:
            request = AnalyzeRequest(directories=[str(repo) for repo in selected_repos])
            print(f"Analyzing {len(selected_repos)} selected repositories...")
        else:
            print("Analyzing all discovered repositories...")
        
        # Rich progress bar (per-repository).
        # Note: analyze_zip emits prints; redirecting stdout/stderr prevents the bar
        # from being corrupted by regular print output.
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TextColumn("{task.fields[repo_name]}"),
            transient=False,
            redirect_stdout=True,
            redirect_stderr=True,
            expand=True,
        )

        task_id: int | None = None

        def progress_callback(current: int, total: int, repo_name: str) -> None:
            nonlocal task_id
            if task_id is None:
                task_id = progress.add_task(
                    "Analyzing repositories",
                    total=total,
                    repo_name=repo_name,
                )
            progress.update(
                task_id,
                total=total,
                completed=current,
                repo_name=repo_name,
            )

        with progress:
            expected_total = len(selected_repos) if selected_repos else 0
            if expected_total > 0:
                task_id = progress.add_task(
                    "Analyzing repositories",
                    total=expected_total,
                    repo_name="Starting...",
                )
            analyze_result = await analyze_zip(
                zip_id=active_zip_id,
                request=request,
                db=db,
                progress_callback=progress_callback,
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
        extraction_path_str = str(analyze_result.extraction_path)
        
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

        # Display timeline and chronology views
        display_project_timeline(db, extraction_path_str)
        display_skills_chronology(db, extraction_path_str)
        
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


def parse_selection(selection: str, max_idx: int) -> list[int]:
    """Parse user selection string into list of indices.
    
    Supports:
    - Single numbers: "1", "3"
    - Comma-separated: "1,3,5"
    - Ranges: "1-3" (expands to 1,2,3)
    - Mixed: "1,3-5,7"
    - "all" for all items
    
    Returns 0-indexed list of valid indices.
    """
    selection = selection.strip().lower()
    if selection == "all":
        return list(range(max_idx))
    
    indices: set[int] = set()
    parts = selection.replace(" ", "").split(",")
    
    for part in parts:
        if not part:
            continue
        if "-" in part:
            try:
                start, end = part.split("-", 1)
                start_idx = int(start) - 1  # Convert to 0-indexed
                end_idx = int(end) - 1
                if 0 <= start_idx <= end_idx < max_idx:
                    indices.update(range(start_idx, end_idx + 1))
            except ValueError:
                continue
        else:
            try:
                idx = int(part) - 1  # Convert to 0-indexed
                if 0 <= idx < max_idx:
                    indices.add(idx)
            except ValueError:
                continue
    
    return sorted(indices)


def prompt_repo_selection(repos: list[Path]) -> list[Path]:
    """Display discovered repos and let user select which to analyze."""
    print("Step 4: Select Repositories")
    print("-" * 40)
    print(f"Discovered {len(repos)} git repositories:\n")
    
    for idx, repo in enumerate(repos, 1):
        print(f"  [{idx}] {repo.name}")
    
    print()
    print("Enter selection (e.g., '1,3,5' or '1-3' or 'all'):")
    
    while True:
        selection = input("Selection (default: all): ").strip() or "all"
        indices = parse_selection(selection, len(repos))
        
        if not indices:
            print("No valid selection. Please try again.")
            continue
        
        selected = [repos[i] for i in indices]
        print(f"\nSelected {len(selected)} repositories:")
        for repo in selected:
            print(f"  ✓ {repo.name}")
        print()
        return selected


def display_progress(current: int, total: int, repo_name: str) -> None:
    """Display analysis progress for a repository."""
    print(f"  [{current}/{total}] Analyzing {repo_name}...")


def display_project_timeline(db: Session, extraction_path: str) -> None:
    """Display project timeline for analyzed repos."""
    from datetime import timedelta
    from artifactminer.helpers.time import utcnow
    from artifactminer.db.models import RepoStat
    
    print("\n" + "=" * 60)
    print("                  PROJECT TIMELINE")
    print("=" * 60 + "\n")
    
    # Query repos from this extraction (similar to projects.py logic)
    now = utcnow()
    six_months_ago = now - timedelta(days=180)
    
    repo_stats = (
        db.query(RepoStat)
        .filter(
            RepoStat.first_commit.isnot(None),
            RepoStat.last_commit.isnot(None),
            RepoStat.deleted_at.is_(None),
            RepoStat.project_path.like(f"{extraction_path}%")
        )
        .order_by(RepoStat.first_commit.asc())
        .all()
    )
    
    if not repo_stats:
        print("  No timeline data available.\n")
        return
    
    for stat in repo_stats:
        first = stat.first_commit.strftime("%Y-%m-%d") if stat.first_commit else "?"
        last = stat.last_commit.strftime("%Y-%m-%d") if stat.last_commit else "?"
        duration = (stat.last_commit - stat.first_commit).days if stat.first_commit and stat.last_commit else 0
        active = "●" if stat.last_commit and stat.last_commit >= six_months_ago else "○"
        
        print(f"  {active} {stat.project_name}")
        print(f"      {first} → {last} ({duration} days)")
    
    print()


def display_skills_chronology(db: Session, extraction_path: str) -> None:
    """Display chronological skills progression."""
    from datetime import datetime as dt
    from artifactminer.db.models import ProjectSkill, UserProjectSkill, Skill, RepoStat
    
    print("=" * 60)
    print("                SKILLS CHRONOLOGY")
    print("=" * 60 + "\n")
    
    # Query skills for repos in this extraction (similar to retrieval.py logic)
    items = []
    
    # ProjectSkill results
    project_results = (
        db.query(ProjectSkill, Skill, RepoStat)
        .join(Skill, ProjectSkill.skill_id == Skill.id)
        .join(RepoStat, ProjectSkill.repo_stat_id == RepoStat.id)
        .filter(
            RepoStat.deleted_at.is_(None),
            RepoStat.project_path.like(f"{extraction_path}%")
        )
        .all()
    )
    
    # UserProjectSkill results
    user_results = (
        db.query(UserProjectSkill, Skill, RepoStat)
        .join(Skill, UserProjectSkill.skill_id == Skill.id)
        .join(RepoStat, UserProjectSkill.repo_stat_id == RepoStat.id)
        .filter(
            RepoStat.deleted_at.is_(None),
            RepoStat.project_path.like(f"{extraction_path}%")
        )
        .all()
    )
    
    for skill_record, skill, repo_stat in project_results:
        items.append({
            "date": repo_stat.first_commit,
            "skill": skill.name,
            "project": repo_stat.project_name,
            "category": skill.category,
        })
    
    for skill_record, skill, repo_stat in user_results:
        items.append({
            "date": repo_stat.first_commit,
            "skill": skill.name,
            "project": repo_stat.project_name,
            "category": skill.category,
        })
    
    # Sort by date and deduplicate
    items.sort(key=lambda x: x["date"] or dt.max)
    seen_skills: set[str] = set()
    unique_items = []
    for item in items:
        if item["skill"] not in seen_skills:
            seen_skills.add(item["skill"])
            unique_items.append(item)
    
    if not unique_items:
        print("  No skills data available.\n")
        return
    
    # Group by category
    by_category: dict[str, list] = {}
    for item in unique_items:
        cat = item["category"] or "Other"
        by_category.setdefault(cat, []).append(item)
    
    for category, skills in by_category.items():
        print(f"  {category}:")
        for item in skills:
            date_str = item["date"].strftime("%Y-%m-%d") if item["date"] else "?"
            print(f"    • {item['skill']} (first used: {date_str} in {item['project']})")
        print()


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
    print("Step 5: Output File")
    print("-" * 40)
    if initial is not None:
        validated = _validate_output_path(initial, confirm_overwrite=True)
        if validated is not None:
            print(f"Output: {validated.name}\n")
            return validated
    while True:
        path_str = _strip_wrapping_quotes(input("Enter your output path: write your filename and extension (filename.json or filename.txt): "))
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

        # Step 4: Discover and select repositories
        print("Extracting ZIP to discover repositories...")
        db = SessionLocal()
        try:
            # Copy ZIP to uploads directory
            UPLOADS_DIR.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_filename = f"{timestamp}_{input_path.name}"
            dest_path = UPLOADS_DIR / safe_filename
            shutil.copy2(input_path, dest_path)
            
            # Create upload record
            uploaded_zip = UploadedZip(
                filename=input_path.name,
                path=str(dest_path),
                portfolio_id="cli-generated"
            )
            db.add(uploaded_zip)
            db.commit()
            db.refresh(uploaded_zip)
            
            # Extract ZIP
            extraction_path = extract_zip_to_persistent_location(str(dest_path), uploaded_zip.id)
            uploaded_zip.extraction_path = str(extraction_path)
            db.commit()
            
            # Discover repos
            discovered_repos = discover_git_repos(extraction_path)
            
            if not discovered_repos:
                print("No git repositories found in the ZIP file.")
                sys.exit(1)
            
            print()
            selected_repos = prompt_repo_selection(discovered_repos)
            
            # Save zip_id for run_analysis
            saved_zip_id = uploaded_zip.id
            
        finally:
            db.close()
        
        output_path = prompt_output_file(output_path)

        print("Proceed with analysis? [Y/n]: ", end="")
        if input().strip().lower() not in ("", "y", "yes"):
            print("Cancelled.")
            sys.exit(0)

        print()
        asyncio.run(run_analysis(input_path, output_path, consent, email, selected_repos, saved_zip_id))
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled.")
        sys.exit(0)


def main():
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
