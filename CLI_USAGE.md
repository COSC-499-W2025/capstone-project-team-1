# ArtifactMiner CLI Usage

## Overview
CLI tool to analyze student project portfolios and generate reports. Supports interactive and non-interactive modes.

## Basic Usage
```bash
python -m artifactminer.main
python -m artifactminer.main -i <input.zip> -o <output.txt|json> [options]
```

## Required Arguments (Non-Interactive Mode)
- `-i, --input` - Path to ZIP file containing projects
- `-o, --output` - Output file path (`.txt` for text, `.json` for JSON)

## Optional Arguments
- `-c, --consent` - Consent level: `full`, `no_llm`, `none` (default: `no_llm`)
- `-u, --user-email` - User email for tracking (default: `cli-user@example.com`)

## Interactive Mode
Run without `-i` and `-o` to enter guided prompts. If only one of `-i` or `-o` is provided, the CLI prompts for the missing values and uses any provided flags for the rest.

## Examples

**Interactive mode:**
```bash
python -m artifactminer.main
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
