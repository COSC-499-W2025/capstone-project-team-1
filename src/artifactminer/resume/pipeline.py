from __future__ import annotations

import time
from collections import Counter
from datetime import datetime
from pathlib import Path

from email_validator import EmailNotValidError, validate_email

from artifactminer.api.analyze import discover_git_repos, extract_zip_to_persistent_location
from artifactminer.RepositoryIntelligence.repo_intelligence_main import getRepoStats
from artifactminer.RepositoryIntelligence.repo_intelligence_user import getUserRepoStats
from artifactminer.skills.deep_analysis import DeepRepoAnalyzer

from artifactminer.resume.helpers import collect_user_additions_by_file, should_skip_path
from artifactminer.resume.ollama_client import DEFAULT_MODEL, ensure_model_available
from artifactminer.resume.passes.analysis import analyze_file
from artifactminer.resume.passes.discovery import rank_files
from artifactminer.resume.passes.portfolio import synthesize_portfolio
from artifactminer.resume.passes.synthesis import synthesize_project
from artifactminer.resume.schemas import ResumeArtifacts
from artifactminer.resume.treesitter import get_structural_summary


def _log(verbose: bool, message: str) -> None:
    if verbose:
        print(message)


def _normalize_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(v) for v in value if str(v).strip()]
    return [str(value)]


def _format_date(value: datetime | None) -> str:
    if not value:
        return "unknown"
    return value.date().isoformat()


def _line_count(text: str) -> int:
    return len([line for line in text.splitlines() if line.strip()])


def generate_resume(
    *,
    zip_path: Path,
    user_email: str,
    top_files: int = 15,
    verbose: bool = False,
) -> ResumeArtifacts:
    start_time = time.monotonic()
    ensure_model_available(DEFAULT_MODEL)

    try:
        validate_email(user_email, check_deliverability=False)
    except EmailNotValidError as exc:
        raise ValueError(f"Invalid email address: {user_email}") from exc

    if not zip_path.exists():
        raise ValueError(f"ZIP file not found: {zip_path}")

    try:
        extraction_dir = extract_zip_to_persistent_location(str(zip_path), zip_id=1)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("Failed to extract ZIP file.") from exc

    repos = discover_git_repos(extraction_dir)
    if not repos:
        raise RuntimeError("No git repositories found inside the ZIP.")

    project_summaries = []
    skill_counter: Counter[str] = Counter()

    _log(verbose, f"Found {len(repos)} git repositories.")

    for repo_path in repos:
        repo_name = Path(repo_path).name
        _log(verbose, f"Analyzing repo: {repo_name}")

        try:
            repo_stats = getRepoStats(repo_path)
        except Exception as exc:  # noqa: BLE001
            _log(verbose, f"  Skipping repo stats due to error: {exc}")
            continue

        try:
            user_stats = getUserRepoStats(repo_path, user_email)
        except Exception as exc:  # noqa: BLE001
            _log(verbose, f"  Skipping user stats due to error: {exc}")
            continue

        if not user_stats.total_commits:
            _log(verbose, "  No user commits found. Skipping repo.")
            continue

        additions_by_file = collect_user_additions_by_file(
            repo_path, user_email, max_commits=500
        )
        additions_by_file = {
            path: code
            for path, code in additions_by_file.items()
            if code.strip() and not should_skip_path(path)
        }
        if not additions_by_file:
            _log(verbose, "  No usable additions found. Skipping repo.")
            continue

        deep_result = None
        try:
            deep_result = DeepRepoAnalyzer(enable_llm=False).analyze(
                repo_path=str(repo_path),
                repo_stat=repo_stats,
                user_email=user_email,
                user_contributions={"additions": "\n".join(additions_by_file.values())},
                consent_level="none",
            )
        except Exception as exc:  # noqa: BLE001
            _log(verbose, f"  Skill extraction failed (continuing): {exc}")

        if deep_result:
            for skill in deep_result.skills:
                skill_counter[skill.skill] += 1

        languages_value = getattr(repo_stats, "Languages", None)
        frameworks_value = getattr(repo_stats, "frameworks", None)
        languages_label = ", ".join(_normalize_list(languages_value)) or "unknown"
        frameworks_label = ", ".join(_normalize_list(frameworks_value)) or "none"

        file_line_counts = [
            (path, _line_count(code)) for path, code in additions_by_file.items()
        ]
        file_line_counts.sort(key=lambda item: item[1], reverse=True)

        if len(file_line_counts) > top_files:
            selected_files = rank_files(repo_name, file_line_counts, top_files)
        else:
            selected_files = [path for path, _ in file_line_counts]

        selected_files = selected_files[:top_files]
        _log(verbose, f"  Selected {len(selected_files)} files for analysis.")

        file_analyses = []
        for file_path in selected_files:
            code = additions_by_file.get(file_path, "")
            if not code.strip():
                continue
            summary = get_structural_summary(code, Path(file_path).suffix)
            analysis = analyze_file(
                file_path=file_path,
                project_name=repo_name,
                languages=languages_label,
                frameworks=frameworks_label,
                tree_sitter_summary=summary,
                user_code=code,
                model=DEFAULT_MODEL,
            )
            file_analyses.append(analysis)

        if not file_analyses:
            _log(verbose, "  No file analyses produced. Skipping repo.")
            continue

        skills_list = ""
        if deep_result:
            skills_list = ", ".join(
                [skill.skill for skill in deep_result.skills[:12]]
            )

        project_summary = synthesize_project(
            project_name=repo_name,
            languages=languages_label,
            frameworks=frameworks_label,
            contribution_pct=float(user_stats.userStatspercentages or 0.0),
            total_user_commits=int(user_stats.total_commits or 0),
            first_commit=_format_date(user_stats.first_commit),
            last_commit=_format_date(user_stats.last_commit),
            skills_list=skills_list or "none",
            file_analyses=file_analyses,
            model=DEFAULT_MODEL,
        )

        project_summaries.append(project_summary)

    if not project_summaries:
        raise RuntimeError("No project summaries generated. Check input data.")

    top_skills = [name for name, _ in skill_counter.most_common(8)]
    if not top_skills:
        for summary in project_summaries:
            for tech in summary.technologies:
                if tech not in top_skills:
                    top_skills.append(tech)
                if len(top_skills) >= 8:
                    break
            if len(top_skills) >= 8:
                break

    portfolio_summary = synthesize_portfolio(
        project_summaries, top_skills=top_skills, model=DEFAULT_MODEL
    )

    elapsed = time.monotonic() - start_time

    return ResumeArtifacts(
        projects=project_summaries,
        portfolio_summary=portfolio_summary,
        model_used=DEFAULT_MODEL,
        generation_time_seconds=round(elapsed, 2),
    )
