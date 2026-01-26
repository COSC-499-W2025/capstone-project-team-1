import shutil
import sys
from pathlib import Path
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import or_

from artifactminer.api.analyze import analyze_zip
from artifactminer.api.schemas import AnalyzeRequest
from artifactminer.api.zip import UPLOADS_DIR
from artifactminer.cli.db_setup import setup_consent, setup_user_email
from artifactminer.cli.progress import create_repo_progress
from artifactminer.cli.views import (
    extraction_prefixes,
    display_project_timeline,
    display_skills_chronology,
    display_repo_details,
)
from artifactminer.db import SessionLocal, UploadedZip
from artifactminer.db.models import ResumeItem, UserAIntelligenceSummary, RepoStat
from artifactminer.tui.helpers import export_to_json, export_to_text


def _repo_directory_values(selected_repos: list[Path], extraction_root: str | None) -> list[str]:
    if extraction_root is None:
        return [repo.name for repo in selected_repos]

    root = Path(extraction_root)
    values: list[str] = []
    for repo in selected_repos:
        for candidate_repo in (repo, repo.resolve()):
            for candidate_root in (root, root.resolve()):
                try:
                    values.append(str(candidate_repo.relative_to(candidate_root)))
                    break
                except ValueError:
                    continue
            else:
                continue
            break
        else:
            values.append(repo.name)
    return values


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
            UPLOADS_DIR.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_filename = f"{timestamp}_{input_path.name}"
            dest_path = UPLOADS_DIR / safe_filename

            shutil.copy2(input_path, dest_path)

            uploaded_zip = UploadedZip(
                filename=input_path.name,
                path=str(dest_path),
                portfolio_id="cli-generated",
            )
            db.add(uploaded_zip)
            db.commit()
            db.refresh(uploaded_zip)

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

