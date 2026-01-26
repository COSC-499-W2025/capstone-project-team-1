import sys
from pathlib import Path

BANNER_ART = r"""
    _         _   _  __            _     __  __ _                 
   / \   _ __| |_(_)/ _| __ _  ___| |_  |  \/  (_)_ __   ___ _ __ 
  / _ \ | '__| __| | |_ / _` |/ __| __| | |\/| | | '_ \ / _ \ '__|
 / ___ \| |  | |_| |  _| (_| | (__| |_  | |  | | | | | |  __/ |   
/_/   \_\_|   \__|_|_|  \__,_|\___|\__| |_|  |_|_|_| |_|\___|_|   
""".strip("\n")


def print_header() -> None:
    """Print the interactive CLI header."""
    print("\n" + "=" * 60)
    print(BANNER_ART)
    print("Student Portfolio Analysis Tool")
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


def validate_input_path(path):
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


def validate_output_path(path, confirm_overwrite: bool = False):
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


def prompt_path(
    *,
    step_title: str,
    prompt_text: str,
    validator,
    initial=None,
    on_success=None,
) -> Path:
    print(step_title)
    print("-" * 40)

    if initial is not None:
        validated = validator(initial)
        if validated is not None:
            if on_success:
                on_success(validated)
            return validated

    while True:
        raw = _strip_wrapping_quotes(input(prompt_text))
        if not raw:
            print("Please enter a path.")
            continue
        validated = validator(raw)
        if validated is None:
            continue
        if on_success:
            on_success(validated)
        return validated


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
    def _on_success(path: Path) -> None:
        size_mb = path.stat().st_size / (1024 * 1024)
        print(f"Found: {path.name} ({size_mb:.1f} MB)\n")

    return prompt_path(
        step_title="Step 3: Input File",
        prompt_text="Enter path to ZIP file: ",
        validator=validate_input_path,
        initial=initial,
        on_success=_on_success,
    )


def prompt_output_file(initial=None) -> Path:
    def _on_success(path: Path) -> None:
        print(f"Output: {path.name}\n")

    return prompt_path(
        step_title="Step 5: Output File",
        prompt_text="Enter output path (.json or .txt): ",
        validator=lambda p: validate_output_path(p, confirm_overwrite=True),
        initial=initial,
        on_success=_on_success,
    )


def confirm_or_exit(prompt: str) -> None:
    print(prompt, end="")
    if input().strip().lower() not in ("", "y", "yes"):
        print("Cancelled.")
        sys.exit(0)
