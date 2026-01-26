# ArtifactMiner CLI Usage

## Overview
CLI tool to analyze student project portfolios and generate reports. Supports interactive and non-interactive modes.

## Basic Usage
```bash
python -m artifactminer.main
uv run python -m artifactminer.main
python -m artifactminer.main -i <input.zip> -o <output.txt|json> [options]
uv run python -m artifactminer.main -i <input.zip> -o <output.txt|json> [options]
```

## Required Arguments (Non-Interactive Mode)
- `-i, --input` - Path to ZIP file containing projects
- `-o, --output` - Output file path (`.txt` for text, `.json` for JSON)

## Optional Arguments
- `-c, --consent` - Consent level: `full`, `no_llm`, `none` (default: `no_llm`)
- `-u, --user-email` - User email for tracking (default: `cli-user@example.com`)

## Interactive Mode
Run without `-i` and `-o` to enter guided prompts. The interactive flow includes:

1. **Step 1: Consent** - Choose consent level (full/no_llm/none)
2. **Step 2: User Information** - Enter your email address
3. **Step 3: Input File** - Path to ZIP file containing projects
4. **Step 4: Select Repositories** - Choose which git repos to analyze:
   - Enter `all` to analyze all discovered repositories
   - Enter specific numbers: `1,3,5`
   - Enter ranges: `1-3`
   - Mix formats: `1,3-5,7`
5. **Step 5: Output File** - Path for the report (.json or .txt)

After analysis completes, the CLI displays:
- **Project Timeline** - Shows each project's activity period (first commit → last commit)
- **Skills Chronology** - Shows when skills were first demonstrated, grouped by category

## Examples

**Interactive mode:**
```bash
python -m artifactminer.main
uv run python -m artifactminer.main
```

**Text export with no LLM:**
```bash
python -m artifactminer.main -i projects.zip -o report.txt -c no_llm
```

**JSON export with full consent:**
```bash
python -m artifactminer.main -i projects.zip -o report.json -c full -u student@school.edu
```

**Minimal analysis (no LLM, default email):**
```bash
python -m artifactminer.main -i projects.zip -o report.txt
```

## Output Formats

**Text (`.txt`)**: Human-readable report with three sections:
- PROJECT ANALYSIS DETAILS (metrics per project)
- AI SUMMARIES (top 3 projects)
- RESUME ITEMS (extracted insights)

**JSON (`.json`)**: Structured data with `exported_at`, `project_analyses`, `summaries`, and `resume_items` fields.

## Post-Analysis Display

After exporting results, the CLI shows two visualizations:

**Project Timeline:**
```
● project-alpha
    2023-01-15 → 2024-06-20 (521 days)
○ project-beta
    2022-03-01 → 2022-08-15 (167 days)
```
- ● = Recently active (within 6 months)
- ○ = Inactive

**Skills Chronology:**
```
Languages:
  • Python (first used: 2022-03-01 in project-beta)
  • JavaScript (first used: 2023-01-15 in project-alpha)
Frameworks:
  • React (first used: 2023-02-20 in project-alpha)
```
