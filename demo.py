"""Command-line script demonstrating the current Artifact Miner API surface.

This walkthrough intentionally uses the real endpoints that exist on this
branch today (health, questions/answers, consent, zip upload, directory
listing, and the OpenAI helper). For future milestones the helper functions
remain in place with TODO markers so they can be swapped over to the richer
endpoints (analysis orchestrator, reports, rankings, skills, exports, delete,
etc.) once those routes land in the API.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

import requests

BASE_URL = "http://127.0.0.1:8000"
DEMO_ZIP_PATH = Path("tests/directorycrawler/mocks/mockdirectory_zip.zip")
DEMO_EMAIL = "demo@example.com"
DEMO_PROMPT = (
    "Summarize how Artifact Miner might help a student highlight their best work."
)


def print_heading(title: str) -> None:
    """Render a simple heading for the CLI output."""
    print(f"\n== {title} ==")


def pretty_print(payload: Any) -> None:
    """Dump JSON payloads in a readable format."""
    print(json.dumps(payload, indent=2, sort_keys=True))


def check_health(session: requests.Session, base_url: str) -> Dict[str, Any]:
    response = session.get(f"{base_url}/health", timeout=10)
    response.raise_for_status()
    return response.json()


def fetch_questions(session: requests.Session, base_url: str) -> list[dict[str, Any]]:
    response = session.get(f"{base_url}/questions", timeout=10)
    response.raise_for_status()
    return response.json()


def submit_answers(
    session: requests.Session,
    base_url: str,
    answers: Dict[str, str],
) -> list[dict[str, Any]]:
    payload = {"answers": answers}
    response = session.post(f"{base_url}/answers", json=payload, timeout=10)
    response.raise_for_status()
    return response.json()


def set_consent(
    session: requests.Session,
    base_url: str,
    consent_level: str,
) -> dict[str, Any]:
    payload = {"consent_level": consent_level}
    response = session.put(f"{base_url}/consent", json=payload, timeout=10)
    response.raise_for_status()
    return response.json()


def upload_zip(
    session: requests.Session,
    base_url: str,
    zip_path: Path,
) -> dict[str, Any]:
    with zip_path.open("rb") as handle:
        files = {"file": (zip_path.name, handle, "application/zip")}
        response = session.post(f"{base_url}/zip/upload", files=files, timeout=30)
    response.raise_for_status()
    return response.json()


def list_zip_directories(
    session: requests.Session,
    base_url: str,
    zip_id: int,
) -> dict[str, Any]:
    response = session.get(f"{base_url}/zip/{zip_id}/directories", timeout=10)
    response.raise_for_status()
    return response.json()


def call_openai(
    session: requests.Session,
    base_url: str,
    prompt: str,
) -> dict[str, Any]:
    payload = {"prompt": prompt}
    response = session.post(f"{base_url}/openai", json=payload, timeout=30)
    response.raise_for_status()
    return response.json()


def run_orchestrator(
    session: requests.Session,
    base_url: str,
    zip_id: int,
    user_email: str,
) -> dict[str, Any]:
    """Placeholder for Nathan's ingest/analyze endpoint.

    TODO: Replace this stub with a real POST /analyze/{zip_id} once that route
    lands. It will trigger repo analysis, ranking, and summary generation.
    """
    print(
        "[TODO] Repo analysis orchestrator is not available on this branch. "
        "Skipping automated analysis for zip_id=%s." % zip_id
    )
    return {"status": "skipped", "zip_id": zip_id, "user_email": user_email}


def show_reports(session: requests.Session, base_url: str) -> dict[str, Any]:
    """Placeholder for Brendan's report endpoints.

    TODO: Query /reports/{project_id} (and related endpoints) once merged so we
    can display compiled project intelligence in the demo.
    """
    print("[TODO] Reports API not merged yet. Nothing to display.")
    return {}


def show_skills(session: requests.Session, base_url: str) -> dict[str, Any]:
    """Placeholder for Stavan & Shlok's skill/resume endpoints.

    TODO: Wire up GET /skills/chronology, GET /resume, and GET /summaries when
    those endpoints exist so the demo surfaces stored insights.
    """
    print("[TODO] Skill, resume, and summary endpoints are unavailable.")
    return {}


def export_data(session: requests.Session, base_url: str) -> dict[str, Any]:
    """Placeholder for Brendan's export endpoint.

    TODO: Call GET /export/json (or similar) once implemented to showcase the
    downloadable report flow.
    """
    print("[TODO] Export functionality not merged yet.")
    return {}


def delete_project(session: requests.Session, base_url: str, project_id: int | None) -> dict[str, Any]:
    """Placeholder for Shlok's safe delete endpoint.

    TODO: Invoke DELETE /projects/{id} once contiguous project storage exists.
    """
    del project_id  # Unused until the endpoint exists.
    print("[TODO] Project deletion is not wired up in this branch.")
    return {}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Demonstrate the Artifact Miner API using real endpoints."
    )
    parser.add_argument(
        "--base-url",
        default=BASE_URL,
        help=f"Base URL for the API (default: {BASE_URL})",
    )
    parser.add_argument(
        "--zip",
        dest="zip_path",
        default=str(DEMO_ZIP_PATH),
        help=f"Path to a demo ZIP file (default: {DEMO_ZIP_PATH})",
    )
    parser.add_argument(
        "--email",
        default=DEMO_EMAIL,
        help=f"Email used for questionnaire responses (default: {DEMO_EMAIL})",
    )
    parser.add_argument(
        "--prompt",
        default=DEMO_PROMPT,
        help="Prompt to send to the /openai endpoint.",
    )
    parser.add_argument(
        "--consent-level",
        choices=["full", "no_llm", "none"],
        default="full",
        help="Consent level to set before the analysis steps.",
    )
    return parser.parse_args()


def build_answers(email: str) -> Dict[str, str]:
    """Construct a set of responses for the current questionnaire."""
    return {
        "email": email,
        "artifacts_focus": "Code files and accompanying documentation",
        "end_goal": "Generate a concise multi-project showcase",
        "repository_priority": "Focus on git repositories first",
        "file_patterns_include": "*.py,*.md",
        "file_patterns_exclude": "*.log,*.tmp",
    }


def main() -> int:
    args = parse_args()
    base_url = args.base_url.rstrip("/")
    zip_path = Path(args.zip_path).expanduser()
    if not zip_path.exists():
        print(f"Zip file does not exist: {zip_path}")
        return 1

    answers = build_answers(args.email)

    session = requests.Session()

    try:
        print_heading("Checking API Health")
        pretty_print(check_health(session, base_url))

        print_heading("Fetching Questionnaire")
        questions = fetch_questions(session, base_url)
        pretty_print(questions)

        print_heading("Submitting Answers")
        pretty_print(submit_answers(session, base_url, answers))

        print_heading("Setting Consent")
        pretty_print(set_consent(session, base_url, args.consent_level))

        print_heading("Uploading Zip")
        upload_result = upload_zip(session, base_url, zip_path)
        pretty_print(upload_result)
        zip_id = upload_result["zip_id"]

        print_heading("Listing Zip Directories")
        pretty_print(list_zip_directories(session, base_url, zip_id))

        print_heading("Calling OpenAI Helper")
        pretty_print(call_openai(session, base_url, args.prompt))

        print_heading("Running Analysis Orchestrator")
        pretty_print(run_orchestrator(session, base_url, zip_id, args.email))

        print_heading("Fetching Reports")
        pretty_print(show_reports(session, base_url))

        print_heading("Showing Skills & Resume Entries")
        pretty_print(show_skills(session, base_url))

        print_heading("Exporting Portfolio Data")
        pretty_print(export_data(session, base_url))

        print_heading("Deleting Demo Project")
        pretty_print(delete_project(session, base_url, project_id=None))

        print("\nDemo finished. Future steps are marked with TODO placeholders.")
        return 0
    except requests.HTTPError as exc:
        print(f"HTTP error: {exc.response.status_code} {exc.response.text}")
    except requests.RequestException as exc:
        print(f"Request failed: {exc}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
