from __future__ import annotations

SYSTEM_PROMPT = (
    "You are a professional resume writer and technical recruiter with expertise in "
    "software engineering. You analyze code contributions and produce resume-ready "
    "content. Be concise, factual, and achievement-oriented. "
    "Never fabricate skills or accomplishments — only describe what is evident from the code."
)


def build_file_discovery_prompt(project_name: str, file_list: str, top_n: int) -> str:
    return (
        f"Below is a list of files modified by a developer in the project \"{project_name}\". "
        "Rank them by importance for a resume — which files best demonstrate technical "
        "skill and accomplishment?\n\n"
        f"Files:\n{file_list}\n\n"
        f"Rank the top {top_n} files. Prioritize:\n"
        "- Core application logic over config/boilerplate\n"
        "- Files with significant additions over minor edits\n"
        "- Backend logic, algorithms, and architecture over styling/assets\n"
    )


def build_file_analysis_prompt(
    file_path: str,
    project_name: str,
    languages: str,
    frameworks: str,
    tree_sitter_header: str,
    user_code: str,
    code_omitted: bool,
) -> str:
    omission_note = (
        "Code additions omitted due to length. Use the structural summary only.\n\n"
        if code_omitted
        else ""
    )
    return (
        f"Analyze this developer's code contribution to the file \"{file_path}\" in the "
        f"project \"{project_name}\" (a {languages} project using {frameworks}).\n\n"
        f"Structural summary:\n{tree_sitter_header}\n\n"
        f"{omission_note}"
        "Code additions by the developer:\n"
        "```\n"
        f"{user_code}\n"
        "```\n\n"
        "Describe what was built, notable technical decisions, and skills demonstrated. "
        "Be specific to the code — don't speculate beyond what's visible."
    )


def build_project_synthesis_prompt(
    project_name: str,
    languages: str,
    frameworks: str,
    contribution_pct: float,
    total_user_commits: int,
    first_commit: str,
    last_commit: str,
    skills_list: str,
    file_analyses_json: str,
) -> str:
    return (
        f"Synthesize a resume entry for the project \"{project_name}\".\n\n"
        "Project metadata:\n"
        f"- Languages: {languages}\n"
        f"- Frameworks: {frameworks}\n"
        f"- User contribution: {contribution_pct:.2f}% of commits ({total_user_commits} commits)\n"
        f"- Date range: {first_commit} to {last_commit}\n"
        f"- Detected skills: {skills_list}\n\n"
        "File-level analyses:\n"
        f"{file_analyses_json}\n\n"
        "Generate:\n"
        "1. A one-line project description (for resume header)\n"
        "2. 3-5 bullet points starting with action verbs (Developed, Implemented, Architected, etc.)\n"
        "3. Use the format: '[Action verb] [what] using [technology] [quantifiable result if available]'\n"
        "4. Do not repeat the same verb in consecutive bullets\n"
        "5. Technologies list (deduplicated)\n"
    )


def build_portfolio_prompt(all_project_summaries: str, top_skills: str) -> str:
    return (
        "You are writing a developer portfolio summary based on analysis of multiple projects.\n\n"
        f"Project summaries:\n{all_project_summaries}\n\n"
        "Write a professional portfolio summary in markdown that includes:\n"
        "1. A 2-3 sentence professional summary paragraph\n"
        "2. A 'Key Skills' section grouping skills by category\n"
        "3. A 'Cross-Project Themes' section identifying patterns across projects\n"
        "4. Keep the tone professional but not generic — reference specific projects\n\n"
        f"The developer's strongest signal is: {top_skills}\n"
    )
