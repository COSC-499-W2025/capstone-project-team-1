from typing import List, Dict

ActivityKey = ["code", "test", "design", "docs", "config"]

# Classifies the commit activities of the user in teh selected repo path using collect_user_additions() to get the additions then counting keywords and syntax to create a table
#Ex:{
#  "code": {"commits": 45, "lines_added": 1200, "percentage": 60},
#  "test": {"commits": 15, "lines_added": 400, "percentage": 20},
#  "docs": {"commits": 10, "lines_added": 300, "percentage": 15},
#  "config": {"commits": 5, "lines_added": 100, "percentage": 5}
#}


def classify_commit_activities(additions: List[str]) -> dict:
    # base structure
    activity_summary: Dict[str, dict] = {
        key: {"commits": 0, "lines_added": 0} for key in ActivityKey
    }

    # per-commit loop
    for addition in additions:
        lines = addition.splitlines()
        lines_added = len(lines)
        addition_lower = addition.lower()

        # flags so a commit can land in multiple buckets
        is_test = False
        is_docs = False
        is_config = False
        is_design = False

        # --- tests ---
        if (
            " pytest" in addition_lower
            or "unittest" in addition_lower
            or "assert " in addition_lower
            or " describe(" in addition_lower  # JS tests
            or " it(" in addition_lower
        ):
            is_test = True

        # --- docs ---
        if (
            "# " in addition  # markdown heading
            or "## " in addition
            or "documentation" in addition_lower
            or "readme" in addition_lower
        ):
            is_docs = True

        # --- config ---
        if (
            "json" in addition_lower
            or "yaml" in addition_lower
            or "toml" in addition_lower
            or "env" in addition_lower
            or "settings" in addition_lower
        ):
            is_config = True

        # --- design ---
        if (
            "figma" in addition_lower
            or "wireframe" in addition_lower
            or "mockup" in addition_lower
            or "prototype" in addition_lower
        ):
            is_design = True

        # apply classifications
        classified_any = False

        if is_test:
            activity_summary["test"]["commits"] += 1
            activity_summary["test"]["lines_added"] += lines_added
            classified_any = True

        if is_docs:
            activity_summary["docs"]["commits"] += 1
            activity_summary["docs"]["lines_added"] += lines_added
            classified_any = True

        if is_config:
            activity_summary["config"]["commits"] += 1
            activity_summary["config"]["lines_added"] += lines_added
            classified_any = True

        if is_design:
            activity_summary["design"]["commits"] += 1
            activity_summary["design"]["lines_added"] += lines_added
            classified_any = True

        # default bucket → code
        if not classified_any:
            activity_summary["code"]["commits"] += 1
            activity_summary["code"]["lines_added"] += lines_added

    # --- percentages based on lines_added ---
    total_lines = sum(v["lines_added"] for v in activity_summary.values())

    if total_lines > 0:
        # compute raw float percentages
        raw = {
            k: (v["lines_added"] * 100.0) / total_lines
            for k, v in activity_summary.items()
        }
        floored = {k: int(raw[k]) for k in raw}
        remainder = 100 - sum(floored.values())

        # distribute remainder by largest fractional part
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
