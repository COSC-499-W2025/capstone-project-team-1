import asyncio
import shutil
import sys
from datetime import datetime
from pathlib import Path

from artifactminer.api.analyze import discover_git_repos, extract_zip_to_persistent_location
from artifactminer.api.zip import UPLOADS_DIR
from artifactminer.cli.analysis import run_analysis
from artifactminer.cli.prompts import (
    print_header,
    prompt_consent,
    prompt_email,
    prompt_input_file,
    prompt_output_file,
    confirm_or_exit,
)
from artifactminer.cli.selection import prompt_repo_selection
from artifactminer.db import SessionLocal, UploadedZip


def run_interactive(input_path=None, output_path=None, consent=None, email=None) -> None:
    """Run CLI in interactive mode - collect inputs via prompts, then run analysis."""
    try:
        print_header()

        if consent is None:
            consent = prompt_consent()
        if email is None:
            email = prompt_email()

        input_path = prompt_input_file(input_path)

        print("Extracting ZIP to discover repositories...")
        db = SessionLocal()
        try:
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

            extraction_path = extract_zip_to_persistent_location(str(dest_path), uploaded_zip.id)
            uploaded_zip.extraction_path = str(extraction_path)
            db.commit()

            discovered_repos = discover_git_repos(Path(extraction_path))
            if not discovered_repos:
                print("No git repositories found in the ZIP file.")
                sys.exit(1)

            print()
            selected_repos = prompt_repo_selection(discovered_repos)
            saved_zip_id = uploaded_zip.id
        finally:
            db.close()

        output_path = prompt_output_file(output_path)
        confirm_or_exit("Proceed with analysis? [Y/n]: ")

        print()
        asyncio.run(run_analysis(input_path, output_path, consent, email, selected_repos, saved_zip_id))
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled.")
        sys.exit(0)

