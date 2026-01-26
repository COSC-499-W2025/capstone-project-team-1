import shutil
import sys
from pathlib import Path

from sqlalchemy.orm import Session
from sqlalchemy import or_

from artifactminer.api.analyze import analyze_zip
from artifactminer.api.schemas import AnalyzeRequest
from artifactminer.cli.views import (
    extraction_prefixes,
    display_project_timeline,
    display_skills_chronology,
    display_repo_details,
)
from artifactminer.cli.upload import upload_zip
from artifactminer.db import SessionLocal, UploadedZip
from artifactminer.db.models import ResumeItem, UserAIntelligenceSummary, RepoStat
from artifactminer.tui.helpers import export_to_json, export_to_text
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    MofNCompleteColumn,
)
from datetime import datetime, UTC

from artifactminer.db import Consent, Question, UserAnswer


def _repo_directory_values(selected_repos: list[Path], extraction_root: str | None) -> list[str]:
    if not extraction_root:
        return [repo.name for repo in selected_repos]
    root = Path(extraction_root).resolve()
    values: list[str] = []
    for repo in selected_repos:
        resolved = repo.resolve()
        if resolved.is_relative_to(root):
            values.append(str(resolved.relative_to(root)))
        else:
            values.append(repo.name)
    return values


def setup_consent(db: Session, level: str) -> None:
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
    email_question = db.query(Question).filter(Question.key == "email").first()
    if not email_question:
        email_question = Question(key="email", text="What is your email?", order=1)
        db.add(email_question)
        db.commit()
        db.refresh(email_question)

    db.query(UserAnswer).filter(UserAnswer.question_id == email_question.id).delete()
    answer = UserAnswer(
        question_id=email_question.id,
        answer_text=email,
        answered_at=datetime.now(UTC),
    )
    db.add(answer)
    db.commit()


def create_repo_progress(
    expected_total: int | None,
) -> tuple[Progress, callable]:
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
        refresh_per_second=20,
    )

    task_id: int = progress.add_task(
        "Analyzing repositories",
        total=float(expected_total) if expected_total is not None else 1,
        repo_name="Starting...",
    )

    def progress_callback(completed: int, total: int, repo_name: str) -> None:
        total_value = expected_total if expected_total is not None else total
        progress.update(
            task_id,
            total=total_value,
            completed=completed,
            repo_name=repo_name,
            refresh=True,
        )

    return progress, progress_callback


async def run_analysis(
    input_path: Path,
    output_path: Path,
    consent_level: str,
    user_email: str,
    selected_repos: list[Path] | None = None,
    zip_id: int | None = None,
) -> None:
    """Run analysis pipeline with optional repo selection."""
    db: Session = SessionLocal()
    try:
        print(f"Setting consent level: {consent_level}")
        setup_consent(db, consent_level)

        print(f"Setting user email: {user_email}")
        setup_user_email(db, user_email)

        if zip_id is not None:
            uploaded_zip = db.query(UploadedZip).filter(UploadedZip.id == zip_id).first()
            if not uploaded_zip:
                print(f"Error: ZIP with ID {zip_id} not found", file=sys.stderr)
                sys.exit(1)
            print(f"Using existing ZIP (ID: {uploaded_zip.id})")
        else:
            print(f"Uploading ZIP: {input_path}")
            uploaded_zip = upload_zip(db, input_path)

        print(f"\nAnalyzing ZIP (ID: {uploaded_zip.id})...")

        request = None
        expected_total = None
        if selected_repos:
            directories = _repo_directory_values(selected_repos, uploaded_zip.extraction_path)
            request = AnalyzeRequest(directories=directories)
            expected_total = len(selected_repos)
            print(f"Analyzing {len(selected_repos)} selected repositories...")
        else:
            print("Analyzing all discovered repositories...")

        progress, progress_callback = create_repo_progress(expected_total)
        with progress:
            analyze_result = await analyze_zip(
                zip_id=uploaded_zip.id,
                request=request,
                db=db,
                progress_callback=progress_callback,
            )

        display_repo_details(analyze_result)

        print("\nFetching results from analyzed projects...")
        extraction_path_str = (
            str(uploaded_zip.extraction_path)
            if uploaded_zip.extraction_path
            else str(analyze_result.extraction_path)
        )
        prefixes = extraction_prefixes(extraction_path_str)

        resume_items_query = (
            db.query(ResumeItem, RepoStat)
            .join(RepoStat, ResumeItem.repo_stat_id == RepoStat.id)
            .filter(
                RepoStat.deleted_at.is_(None),
                or_(*[RepoStat.project_path.like(f"{prefix}%") for prefix in prefixes]),
            )
        )

        resume_items = [
            {
                "id": item.id,
                "title": item.title,
                "content": item.content,
                "category": item.category,
                "project_name": repo.project_name if repo else None,
            }
            for item, repo in resume_items_query.all()
        ]

        summaries_query = (
            db.query(UserAIntelligenceSummary)
            .filter(
                UserAIntelligenceSummary.user_email == user_email,
                or_(
                    *[
                        UserAIntelligenceSummary.repo_path.like(f"{prefix}%")
                        for prefix in prefixes
                    ]
                ),
            )
        )

        summaries = [{"repo_path": s.repo_path, "summary_text": s.summary_text} for s in summaries_query.all()]
        summary_by_path = {s["repo_path"]: s["summary_text"] for s in summaries}

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
                "error": getattr(repo, "error", None),
            }
            for repo in analyze_result.repos_analyzed
        ]

        print(f"Exporting to: {output_path}")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if output_path.suffix not in (".json", ".txt"):
            print(
                f"Warning: Unsupported output format '{output_path.suffix}'. Supported formats are .json and .txt. Defaulting to .txt"
            )
            output_path = output_path.with_suffix(".txt")

        if output_path.suffix == ".json":
            result_path = export_to_json(resume_items, summaries, output_path.parent, project_analyses)
        else:
            result_path = export_to_text(resume_items, summaries, output_path.parent, project_analyses)

        if result_path.exists():
            shutil.move(str(result_path), str(output_path))

        print(f"✓ Analysis complete! Results saved to: {output_path}")

        display_project_timeline(db, extraction_path_str)
        display_skills_chronology(db, extraction_path_str)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()
