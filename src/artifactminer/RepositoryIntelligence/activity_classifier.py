from typing import List, Dict

ActivityKey = ["code", "test", "design", "docs", "config"]


def classify_commit_activities(additions: List[str]) -> dict:
    """
    Classify commit activity based on added text blobs.

    - A single commit can contribute to multiple categories (test + docs + config, etc.)
    - Docs are detected from comment-only / doc-style lines, and from doc-ish inline comments in the comment portion.
    - Code+comment lines always count as code; their comments may also contribute to docs.
    - Percentages are based on lines_added and normalized to sum to 100 when there is activity.
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
        has_code_activity = False

        doc_like_lines = 0
        config_like_lines = 0
        docs_keyword_hit = False  # track if we saw doc-ish text at all

        for line in non_blank_lines:
            raw = line.rstrip("\n")
            stripped = raw.lstrip()

            # Quick check for HTML comment-only docs (e.g. PR templates)
            if stripped.startswith("<!--"):
                # Treat HTML comment blocks as doc-ish by default
                doc_like_lines += 1
                docs_keyword_hit = True
                continue

            # Split into code vs comment part for languages with #, //, /*.
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

            if has_code:
                has_code_activity = True

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
            # DOCS detection (comment-only / doc-style)
            # --------------------
            if has_comment_only:
                # Markdown-style headings / bullet docs
                if comment_lower.startswith("# ") or comment_lower.startswith("## "):
                    doc_like_lines += 1
                    docs_keyword_hit = True
                # Common doc-ish words
                elif any(
                    kw in comment_lower
                    for kw in [
                        "readme",
                        "documentation",
                        "user guide",
                        "usage:",
                        "example:",
                        "examples:",
                        "parameters",
                        "returns",
                        "notes:",
                        "note:",
                        "warning:",
                        "api reference",
                        "changelog",
                        "release notes",
                    ]
                ):
                    doc_like_lines += 1
                    docs_keyword_hit = True
                # Docstring-only lines (Python) like """Summary"""
                elif stripped.startswith('"""') or stripped.startswith("'''"):
                    # treat short triple-quoted lines as doc-ish
                    doc_like_lines += 1
                    docs_keyword_hit = True

            # Inline comments may also contain doc-like text
            if comment_part_stripped and not has_comment_only:
                if any(
                    kw in comment_lower
                    for kw in [
                        "readme",
                        "documentation",
                        "user guide",
                        "usage:",
                        "example:",
                        "examples:",
                        "parameters",
                        "returns",
                        "notes:",
                        "note:",
                        "warning:",
                        "api reference",
                        "changelog",
                        "release notes",
                    ]
                ):
                    doc_like_lines += 1
                    docs_keyword_hit = True

            # --------------------
            # CONFIG detection (config-like structure)
            # --------------------
            # env-style: FOO=bar (no '==' and uppercase key)
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

        # Decide docs/config based on thresholds
        # Docs: either clear doc keywords or a big chunk of comment-only lines
        if doc_like_lines >= 3 and (doc_like_lines / lines_added) >= 0.2:
            has_docs = True
        elif docs_keyword_hit and doc_like_lines >= 1:
            # a small amount of clearly doc-ish text
            has_docs = True

        # Config: multiple config-like lines and decent proportion
        if config_like_lines >= 3 and (config_like_lines / lines_added) >= 0.2:
            has_config = True

        classified_any = False

        if has_test:
            activity_summary["test"]["commits"] += 1
            activity_summary["test"]["lines_added"] += lines_added
            classified_any = True

        if has_docs:
            activity_summary["docs"]["commits"] += 1
            activity_summary["docs"]["lines_added"] += lines_added
            classified_any = True

        if has_config:
            activity_summary["config"]["commits"] += 1
            activity_summary["config"]["lines_added"] += lines_added
            classified_any = True

        if has_design:
            activity_summary["design"]["commits"] += 1
            activity_summary["design"]["lines_added"] += lines_added
            classified_any = True

        # Default bucket → code
        if not classified_any:
            activity_summary["code"]["commits"] += 1
            activity_summary["code"]["lines_added"] += lines_added

    # --- percentages based on lines_added ---
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
            activity_summary[k]["percentage"] = floored[k]
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
