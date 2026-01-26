from __future__ import annotations

from collections import defaultdict
from datetime import datetime as dt
from pathlib import Path

from sqlalchemy.orm import Session

from artifactminer.api.projects import fetch_project_timeline
from artifactminer.api.retrieval import fetch_skill_chronology
from artifactminer.api.schemas import AnalyzeResponse


def extraction_prefixes(extraction_path: str) -> list[str]:
    if not extraction_path:
        return []
    raw = str(extraction_path)
    resolved = str(Path(raw).resolve())
    return sorted({raw, resolved})


def display_project_timeline(db: Session, extraction_path: str) -> None:
    print("\n" + "=" * 60)
    print("                  PROJECT TIMELINE")
    print("=" * 60 + "\n")

    timeline_items = fetch_project_timeline(
        db,
        project_path_prefixes=extraction_prefixes(extraction_path),
    )

    if not timeline_items:
        print("  No timeline data available.\n")
        return

    for item in timeline_items:
        first = item.first_commit.strftime("%Y-%m-%d") if item.first_commit else "?"
        last = item.last_commit.strftime("%Y-%m-%d") if item.last_commit else "?"
        active = "●" if item.was_active else "○"
        print(f"  {active} {item.project_name}\n      {first} → {last} ({item.duration_days} days)")

    print()


def display_skills_chronology(db: Session, extraction_path: str) -> None:
    print("=" * 60)
    print("                SKILLS CHRONOLOGY")
    print("=" * 60 + "\n")

    items = fetch_skill_chronology(
        db,
        project_path_prefixes=extraction_prefixes(extraction_path),
    )

    if not items:
        print("  No skills data available.\n")
        return

    items.sort(key=lambda item: item.date or dt.max)

    seen: set[str] = set()
    unique_items = [item for item in items if not (item.skill in seen or seen.add(item.skill))]

    by_category: dict[str, list] = defaultdict(list)
    for item in unique_items:
        by_category[item.category or "Other"].append(item)

    for category, skills in by_category.items():
        print(f"  {category}:")
        for item in skills:
            date_str = item.date.strftime("%Y-%m-%d") if item.date else "?"
            print(f"    • {item.skill} (first used: {date_str} in {item.project})")
        print()


def display_repo_details(analyze_result: AnalyzeResponse) -> None:
    print(f"\n{'='*80}")
    print(f"ANALYSIS COMPLETE: {len(analyze_result.repos_analyzed)} repositories analyzed")
    print(f"{'='*80}\n")

    for idx, repo in enumerate(analyze_result.repos_analyzed, 1):
        print(f"\n{'-'*80}")
        print(f"[{idx}] {repo.project_name}")
        print(f"{'-'*80}")
        print(f"  Path: {repo.project_path}")

        if getattr(repo, "error", None):
            print(f"  ⚠ Error: {repo.error}")
            continue

        if repo.languages:
            print(f"  Languages: {', '.join(repo.languages)}")
        if repo.frameworks:
            print(f"  Frameworks: {', '.join(repo.frameworks)}")

        print(f"  Skills extracted: {repo.skills_count}")
        print(f"  Insights generated: {repo.insights_count}")

        if repo.user_contribution_pct is not None:
            print(f"  User contribution: {repo.user_contribution_pct:.1f}%")
        if repo.user_total_commits is not None:
            print(f"  User commits: {repo.user_total_commits}")
        if repo.user_commit_frequency is not None:
            print(f"  Commit frequency: {repo.user_commit_frequency:.2f} commits/week")

        if repo.user_first_commit and repo.user_last_commit:
            first = repo.user_first_commit.strftime("%Y-%m-%d")
            last = repo.user_last_commit.strftime("%Y-%m-%d")
            print(f"  Activity period: {first} → {last}")

    print(f"\n{'='*80}\n")
