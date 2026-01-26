"""ArtifactMiner CLI entry point (interactive and non-interactive)."""

import argparse
import asyncio
import sys
from pathlib import Path

from artifactminer.cli.prompts import validate_input_path, validate_output_path
from artifactminer.cli.selection import parse_selection

__all__ = ["parse_selection"]


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="artifactminer",
        description="Analyze student project portfolios and generate resumes",
    )

    parser.add_argument("-i", "--input", type=Path, help="Path to input ZIP file")
    parser.add_argument(
        "-o", "--output", type=Path, help="Path to output file (.json or .txt)"
    )
    parser.add_argument(
        "-c",
        "--consent",
        choices=["full", "no_llm", "none"],
        default=None,
        help="Consent level for LLM usage (default: no_llm)",
    )
    parser.add_argument(
        "-u",
        "--user-email",
        default=None,
        help="User email for analysis tracking (default: cli-user@example.com)",
    )

    args = parser.parse_args()

    if args.input and args.output:
        from artifactminer.cli.analysis import run_analysis

        input_path = validate_input_path(args.input)
        if input_path is None:
            print(f"Error: Invalid input file: {args.input}", file=sys.stderr)
            sys.exit(1)

        output_path = validate_output_path(args.output, confirm_overwrite=False)
        if output_path is None:
            print(f"Error: Invalid output file: {args.output}", file=sys.stderr)
            sys.exit(1)

        consent = args.consent or "no_llm"
        email = args.user_email or "cli-user@example.com"
        asyncio.run(run_analysis(input_path, output_path, consent, email))
        return

    from artifactminer.cli.interactive import run_interactive

    run_interactive(
        input_path=args.input,
        output_path=args.output,
        consent=args.consent,
        email=args.user_email,
    )


if __name__ == "__main__":
    main()

