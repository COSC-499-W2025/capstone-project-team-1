from typing import List, Dict

ActivityKey = ["code", "test", "design", "docs", "config"]


def classify_commit_activities(additions: List[str]) -> dict:
    """
    Classify commit activity based on added text blobs.

    - A single commit can contribute to multiple categories (code + test + docs + config, etc.)
    - Docs are detected from comment-only lines, inline comments, and Python/HTML doc-like blocks.
    - A line with both code and a comment counts as one code line AND one docs line.
    - Percentages are based on category line counts and normalized to sum to 100.
    """
    activity_summary: Dict[str, dict] = {
        key: {"commits": 0, "lines_added": 0} for key in ActivityKey
    }

    for addition in additions:
        lines = addition.splitlines()
        non_blank_lines = [ln for ln in lines if ln.strip()]
        lines_added = len(non_blank_lines)
        if lines_added == 0:
            continue

        has_test = False
        has_docs = False
        has_config = False
        has_design = False


        code_lines = 0
        doc_like_lines = 0
        config_like_lines = 0

        # Track multi-line Python docstrings
        in_docstring_block = False

        for line in non_blank_lines:
            raw = line.rstrip("\n")
            stripped = raw.strip()

            # --------------------
            # DOCSTRING handling (Python triple-quoted strings)
            # --------------------
            if in_docstring_block:
                # Entire line is considered docs
                doc_like_lines += 1

                if stripped.endswith('"""') or stripped.endswith("'''"):
                    in_docstring_block = False

                # Don't treat as code/config
                continue

            if stripped.startswith('"""') or stripped.startswith("'''"):
                # Opening (or one-line) docstring: docs++
                doc_like_lines += 1

                # Multi-line block if it doesn't close here
                if not (stripped.endswith('"""') or stripped.endswith("'''")) or len(
                    stripped
                ) == 3:
                    in_docstring_block = True

                # Docstrings are treated as docs only, not code
                continue

            # --------------------
            # HTML comment-only docs (e.g. PR templates)
            # --------------------
            if stripped.startswith("<!--"):
                doc_like_lines += 1
                continue

            # --------------------
            # Split into code vs comment part for #, //, /*, etc.
            # --------------------
            comment_markers = ["#", "//", "/*"]
            split_index = None

            for marker in comment_markers:
                idx = raw.find(marker)
                if idx != -1 and (split_index is None or idx < split_index):
                    split_index = idx

            if split_index is None:
                code_part = raw
                comment_part = ""
            else:
                code_part = raw[:split_index]
                comment_part = raw[split_index:]

            code_part_stripped = code_part.strip()
            comment_part_stripped = comment_part.strip()

            has_code = bool(code_part_stripped)
            has_comment_only = (not has_code) and bool(comment_part_stripped)
            has_inline_comment = has_code and bool(comment_part_stripped)

            if has_code:
                code_lines += 1

            code_lower = code_part_stripped.lower()
            comment_lower = comment_part_stripped.lower()
            lower_whole = raw.strip().lower()

            # --------------------
            # TEST detection (code-focused)
            # --------------------
            if code_lower:
                if (
                    "assert " in code_lower
                    or "assert(" in code_lower
                    or "pytest" in code_lower
                    or "unittest" in code_lower
                    or "expect(" in code_lower
                    or "describe(" in code_lower
                    or " it(" in code_lower
                    or code_lower.startswith("def test_")
                    or " test_" in code_lower
                    or code_lower.startswith("test(")
                ):
                    has_test = True

            # --------------------
            # DOCS detection (comments / inline docs)
            # --------------------
            # Pure comment-only lines → docs
            if has_comment_only:
                doc_like_lines += 1

            # Inline comments on code lines → count as docs too
            if has_inline_comment:
                doc_like_lines += 1

            # --------------------
            # CONFIG detection (config-like structure)
            # --------------------
            # env-style: FOO=bar (no '==' and uppercase key)
            if "environ" in raw and "=" in raw:
                config_like_lines += 1

            if (
                "=" in raw
                and "==" not in raw
                and not raw.strip().startswith(("if ", "while ", "for "))
                and raw.split("=", 1)[0].strip().isupper()
            ):
                config_like_lines += 1
            # yaml-style: key: value (no trailing ';', no def/class)
            elif (
                ":" in raw
                and not raw.strip().endswith(";")
                and not raw.lstrip().startswith(("def ", "class "))
            ):
                key_part = raw.split(":", 1)[0].strip()
                if key_part and key_part.replace("-", "_").replace(".", "").isalnum():
                    config_like_lines += 1
            # obvious config keywords on simple lines
            elif any(
                kw in lower_whole
                for kw in ["toml", "yaml", "yml", "json", "settings", "config"]
            ):
                if len(raw.strip().split()) <= 4:
                    config_like_lines += 1

            # --------------------
            # DESIGN detection (comment-only or doc-style references)
            # --------------------
            if has_comment_only:
                if any(
                    kw in comment_lower
                    for kw in [
                        "figma",
                        "wireframe",
                        "mockup",
                        "prototype",
                        "ui spec",
                        "ux spec",
                        "screen flow",
                        "user flow",
                    ]
                ):
                    has_design = True

        # Decide docs/config based on line counts
        if doc_like_lines > 0:
            has_docs = True

        if config_like_lines > 0:
            has_config = True

        # --- accumulate per-category stats ---
        if has_test:
            activity_summary["test"]["commits"] += 1
            activity_summary["test"]["lines_added"] += lines_added  # commit-level

        if has_docs:
            activity_summary["docs"]["commits"] += 1
            activity_summary["docs"]["lines_added"] += doc_like_lines

        if has_config:
            activity_summary["config"]["commits"] += 1
            activity_summary["config"]["lines_added"] += config_like_lines

        if has_design:
            activity_summary["design"]["commits"] += 1
            activity_summary["design"]["lines_added"] += lines_added

        if code_lines > 0:
            activity_summary["code"]["commits"] += 1
            activity_summary["code"]["lines_added"] += code_lines

    # --- percentages based on category line counts ---
    total_lines = sum(v["lines_added"] for v in activity_summary.values())

    if total_lines > 0:
        raw = {
            k: (v["lines_added"] * 100.0) / total_lines
            for k, v in activity_summary.items()
        }
        floored = {k: int(raw[k]) for k in raw}
        remainder = 100 - sum(floored.values())

        frac = {k: raw[k] - floored[k] for k in raw}
        keys_ordered = sorted(frac.keys(), key=lambda k: frac[k], reverse=True)

        idx = 0
        while remainder != 0 and keys_ordered:
            key = keys_ordered[idx % len(keys_ordered)]
            floored[key] += 1
            remainder -= 1
            idx += 1

        for k in ActivityKey:
            activity_summary[k]["percentage"] = floored.get(k, 0)
    else:
        for k in ActivityKey:
            activity_summary[k]["percentage"] = 0

    return activity_summary


def print_activity_summary(activity_summary: dict):
    print(f"{'Activity':<10} {'Commits':<10} {'Lines Added':<15} {'Percentage':<10}")
    print("-" * 50)
    for activity, stats in activity_summary.items():
        print(
            f"{activity:<10} "
            f"{stats['commits']:<10} "
            f"{stats['lines_added']:<15} "
            f"{stats['percentage']:<10d}"
        )
