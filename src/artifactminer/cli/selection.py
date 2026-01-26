from pathlib import Path


def parse_selection(selection: str, max_idx: int) -> list[int]:
    """Parse user selection string into list of indices (0-indexed)."""
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
                start_idx = int(start) - 1
                end_idx = int(end) - 1
                if 0 <= start_idx <= end_idx < max_idx:
                    indices.update(range(start_idx, end_idx + 1))
            except ValueError:
                continue
        else:
            try:
                idx = int(part) - 1
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

