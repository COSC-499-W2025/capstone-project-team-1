# Repository Intelligence Module - API Documentation

Comprehensive guide to all methods in the Repository Intelligence module, organized by file.

---

## Table of Contents
- [repo_intelligence_main.py](#repo_intelligence_mainpy)
- [repo_intelligence_user.py](#repo_intelligence_userpy)
- [repo_intelligence_AI.py](#repo_intelligence_aipy)
- [activity_classifier.py](#activity_classifierpy)
- [framework_detector.py](#framework_detectorpy)

---

## repo_intelligence_main.py

Core repository analysis functions for extracting basic statistics and metadata from Git repositories.

### `isGitRepo(path)`

**Description:** Checks whether a given path is a valid Git repository by verifying the existence of a `.git` directory.

**Parameters:**
- `path` (os.PathLike | str): Path to check

**Returns:** `bool` - True if the path contains a `.git` directory, False otherwise

**Example:**
```python
from artifactminer.RepositoryIntelligence.repo_intelligence_main import isGitRepo

if isGitRepo("/path/to/my/project"):
    print("Valid Git repository!")
```

---

### `runGit(repo_path, args)`

**Description:** Executes a Git command in the specified repository and returns the output.

**Parameters:**
- `repo_path` (Pathish): Path to the Git repository
- `args` (Iterable[str]): Git command arguments (e.g., `["status", "--short"]`)

**Returns:** `str` - Standard output from the Git command

**Raises:** `CalledProcessError` if the Git command fails

**Example:**
```python
from artifactminer.RepositoryIntelligence.repo_intelligence_main import runGit

# Check if inside a work tree
output = runGit("/path/to/repo", ["rev-parse", "--is-inside-work-tree"])
print(output)  # "true"
```

---

### `getRepoStats(repo_path)`

**Description:** Analyzes a Git repository and extracts comprehensive statistics including language usage, commit history, collaboration status, and detected frameworks.

**Parameters:**
- `repo_path` (Pathish): Path to the Git repository

**Returns:** `RepoStats` - Dataclass containing:
- `project_name` (str): Repository folder name
- `project_path` (str): Full path to repository
- `is_collaborative` (bool): Whether multiple authors contributed
- `Languages` (List[str]): List of file extensions found
- `language_percentages` (List[float]): Percentage distribution of languages
- `primary_language` (str): Most common file extension
- `first_commit` (datetime): Timestamp of oldest commit
- `last_commit` (datetime): Timestamp of newest commit
- `total_commits` (int): Total number of commits
- `frameworks` (List[str]): Detected frameworks/libraries

**Raises:** `ValueError` if the path is not a Git repository

**Example:**
```python
from artifactminer.RepositoryIntelligence.repo_intelligence_main import getRepoStats

stats = getRepoStats("/path/to/my/project")
print(f"Project: {stats.project_name}")
print(f"Primary Language: {stats.primary_language}")
print(f"Total Commits: {stats.total_commits}")
print(f"Frameworks: {stats.frameworks}")
```

---

### `saveRepoStats(stats)`

**Description:** Persists a `RepoStats` object to the database in the `RepoStat` table.

**Parameters:**
- `stats` (RepoStats): Repository statistics object to save

**Returns:** None

**Side Effects:** Inserts a new row in the `RepoStat` database table

**Example:**
```python
from artifactminer.RepositoryIntelligence.repo_intelligence_main import getRepoStats, saveRepoStats

stats = getRepoStats("/path/to/repo")
saveRepoStats(stats)
print("Repository stats saved to database!")
```

---

## repo_intelligence_user.py

User-specific repository analysis functions for tracking individual contributions, commit activities, and generating AI-powered summaries.

### `getUserRepoStats(repo_path, user_email)`

**Description:** Analyzes a user's contributions to a repository, including commit count, contribution percentage, commit frequency, and activity breakdown.

**Parameters:**
- `repo_path` (Pathish): Path to the Git repository
- `user_email` (str): Email address of the user to analyze

**Returns:** `UserRepoStats` - Dataclass containing:
- `project_name` (str): Repository name
- `project_path` (str): Full repository path
- `first_commit` (datetime): User's first commit timestamp
- `last_commit` (datetime): User's last commit timestamp
- `total_commits` (int): Number of commits by this user
- `userStatspercentages` (float): Percentage of total commits made by user
- `commitFrequency` (float): Average commits per week
- `commitActivities` (dict): Breakdown of activity types (code/test/docs/config/design)

**Raises:** 
- `ValueError` if path is not a Git repository
- `EmailNotValidError` if email format is invalid

**Example:**
```python
from artifactminer.RepositoryIntelligence.repo_intelligence_user import getUserRepoStats

user_stats = getUserRepoStats("/path/to/repo", "developer@example.com")
print(f"User contributed {user_stats.userStatspercentages:.1f}% of commits")
print(f"Commit frequency: {user_stats.commitFrequency:.2f} commits/week")
print(f"Activities: {user_stats.commitActivities}")
```

---

### `collect_user_additions(repo_path, user_email, ...)`

**Description:** Extracts all lines added by a specific user across their commits, useful for analyzing code contributions and generating summaries.

**Parameters:**
- `repo_path` (Pathish): Path to Git repository
- `user_email` (str): User's email address
- `since` (Optional[str]): Start date/reference (e.g., "2025-10-01" or "2.weeks") - default: None (from beginning)
- `until` (str): End reference - default: "HEAD"
- `max_commits` (int): Maximum commits to process - default: 500
- `skip_merges` (bool): Whether to skip merge commits - default: True
- `max_patch_bytes` (int): Maximum bytes per commit patch - default: 200,000

**Returns:** `List[str]` - List where each item is the combined added lines from one commit (oldest to newest)

**Raises:**
- `ValueError` if path is not a Git repository or email is invalid

**Example:**
```python
from artifactminer.RepositoryIntelligence.repo_intelligence_user import collect_user_additions

additions = collect_user_additions(
    repo_path="/path/to/repo",
    user_email="dev@example.com",
    since="2025-01-01",
    max_commits=100
)
print(f"User made {len(additions)} commits with additions")
```

---

### `saveUserRepoStats(stats)`

**Description:** Persists user-specific repository statistics to the database.

**Parameters:**
- `stats` (UserRepoStats): User statistics object to save

**Returns:** None

**Side Effects:** Inserts a new row in the `UserRepoStat` database table

**Example:**
```python
from artifactminer.RepositoryIntelligence.repo_intelligence_user import getUserRepoStats, saveUserRepoStats

user_stats = getUserRepoStats("/path/to/repo", "user@example.com")
saveUserRepoStats(user_stats)
```

---

### `generate_summaries_for_ranked(db, top=3)`

**Description:** Generates AI-powered summaries for the top-ranked repositories based on ranking scores. Creates both template-based and LLM-enhanced summaries (if user has consented).

**Parameters:**
- `db` (Session): SQLAlchemy database session
- `top` (int): Number of top repositories to summarize - default: 3

**Returns:** `List[dict]` - List of dictionaries containing:
- `project_name` (str): Repository name
- `summary` (str): Generated summary text

**Side Effects:** 
- Saves summaries to `UserAIntelligenceSummary` table
- Queries `RepoStat`, `UserRepoStat`, and `UserAnswer` tables

**Example:**
```python
from artifactminer.db.database import SessionLocal
from artifactminer.RepositoryIntelligence.repo_intelligence_user import generate_summaries_for_ranked

db = SessionLocal()
try:
    summaries = generate_summaries_for_ranked(db, top=5)
    for summary in summaries:
        print(f"{summary['project_name']}: {summary['summary']}")
finally:
    db.close()
```

---

### `extract_added_lines(patch_text)`

**Description:** Helper function to parse a unified diff and extract only the added lines (lines starting with `+`).

**Parameters:**
- `patch_text` (str): Unified diff output from Git

**Returns:** `str` - Newline-separated string of added lines

**Example:**
```python
from artifactminer.RepositoryIntelligence.repo_intelligence_user import extract_added_lines

diff_output = """
--- a/file.py
+++ b/file.py
@@ -1,3 +1,4 @@
 def hello():
+    print("Hello, world!")
     return True
"""
added = extract_added_lines(diff_output)
print(added)  # '    print("Hello, world!")'
```

---

### `split_text_into_chunks(text, max_chunk_size)`

**Description:** Splits a large text string into smaller chunks of specified maximum size.

**Parameters:**
- `text` (str): Text to split
- `max_chunk_size` (int): Maximum characters per chunk

**Returns:** `List[str]` - List of text chunks

**Example:**
```python
from artifactminer.RepositoryIntelligence.repo_intelligence_user import split_text_into_chunks

long_text = "A" * 10000
chunks = split_text_into_chunks(long_text, max_chunk_size=3000)
print(f"Split into {len(chunks)} chunks")
```

---

## repo_intelligence_AI.py

AI-powered analysis functions using LLM to generate intelligent summaries of code contributions.

### `user_allows_llm()`

**Description:** Checks if the user has consented to LLM usage by querying the consent table.

**Parameters:** None

**Returns:** `bool` - True if user has "full" consent level, False otherwise

**Example:**
```python
from artifactminer.RepositoryIntelligence.repo_intelligence_AI import user_allows_llm

if user_allows_llm():
    print("User has consented to AI analysis")
else:
    print("User has not consented - using template summaries")
```

---

### `set_user_consent(level)`

**Description:** Sets the user's consent level for LLM usage in the database.

**Parameters:**
- `level` (str): Consent level (e.g., "full", "none", "partial")

**Returns:** None

**Side Effects:** Updates or inserts consent record in database

**Example:**
```python
from artifactminer.RepositoryIntelligence.repo_intelligence_AI import set_user_consent

set_user_consent("full")
print("User consent set to 'full'")
```

---

### `group_additions_into_blocks(additions, max_blocks=5, max_chars_per_block=8000)`

**Description:** Groups a list of commit additions into a limited number of text blocks for efficient LLM processing. Prevents overwhelming the AI with too much content.

**Parameters:**
- `additions` (List[str]): List of commit addition strings
- `max_blocks` (int): Maximum number of blocks to create - default: 5
- `max_chars_per_block` (int): Maximum characters per block - default: 8000

**Returns:** `List[str]` - List of merged text blocks (up to `max_blocks` items)

**Example:**
```python
from artifactminer.RepositoryIntelligence.repo_intelligence_AI import group_additions_into_blocks

additions = ["commit1 changes...", "commit2 changes...", "commit3 changes..."]
blocks = group_additions_into_blocks(additions, max_blocks=2, max_chars_per_block=5000)
print(f"Grouped {len(additions)} commits into {len(blocks)} blocks for AI processing")
```

---

### `createAIsummaryFromUserAdditions(additions)`

**Description:** Creates an AI-generated summary of user code contributions using LLM analysis. Analyzes each commit addition and synthesizes a final portfolio-ready summary highlighting strengths and technical skills.

**Parameters:**
- `additions` (List[str]): List of commit addition strings

**Returns:** `str` - AI-generated summary text

**Raises:** Returns early messages if no additions or user hasn't consented

**Example:**
```python
from artifactminer.RepositoryIntelligence.repo_intelligence_AI import createAIsummaryFromUserAdditions

additions = ["+ def calculate_sum(a, b):\n+     return a + b"]
summary = createAIsummaryFromUserAdditions(additions)
print(summary)
```

---

### `createSummaryFromUserAdditions(additions)`

**Description:** Wrapper function that creates summaries based on user consent. Uses AI if consented, otherwise returns a placeholder message.

**Parameters:**
- `additions` (List[str]): List of commit addition strings

**Returns:** `str` - Summary text (AI-generated or placeholder)

**Example:**
```python
from artifactminer.RepositoryIntelligence.repo_intelligence_AI import createSummaryFromUserAdditions, set_user_consent

set_user_consent("full")
additions = ["+ print('Hello, world!')"]
summary = createSummaryFromUserAdditions(additions)
print(summary)
```

---

### `saveUserIntelligenceSummary(repo_path, user_email, summary_text)`

**Description:** Saves a generated AI summary to the database.

**Parameters:**
- `repo_path` (str): Repository path
- `user_email` (str): User's email address
- `summary_text` (str): Generated summary text

**Returns:** None

**Side Effects:** Inserts a row into `UserAIntelligenceSummary` table

**Example:**
```python
from artifactminer.RepositoryIntelligence.repo_intelligence_AI import saveUserIntelligenceSummary

saveUserIntelligenceSummary(
    repo_path="/path/to/repo",
    user_email="user@example.com",
    summary_text="User demonstrated strong Python skills..."
)
```

---

## activity_classifier.py

Intelligent commit activity classification system that categorizes code changes into different activity types.

### `classify_commit_activities(additions)`

**Description:** Analyzes commit additions and classifies them into activity categories: code, test, docs, config, and design. Returns detailed statistics including commit counts, lines added, and percentage distribution.

**Parameters:**
- `additions` (List[str]): List of commit addition strings (from `collect_user_additions`)

**Returns:** `dict` - Dictionary with structure:
```python
{
    "code": {"commits": int, "lines_added": int, "percentage": int},
    "test": {"commits": int, "lines_added": int, "percentage": int},
    "docs": {"commits": int, "lines_added": int, "percentage": int},
    "config": {"commits": int, "lines_added": int, "percentage": int},
    "design": {"commits": int, "lines_added": int, "percentage": int}
}
```

**Classification Logic:**
- **code**: Default category for functional code
- **test**: Contains `assert`, `pytest`, `unittest`, `expect()`, `describe()`, `it()`, `test_*` patterns
- **docs**: Comment-only lines, markdown headers, docstrings, README content, documentation keywords
- **config**: YAML/TOML/JSON structures, environment variables, settings files
- **design**: References to Figma, wireframes, mockups, UI/UX specs

**Example:**
```python
from artifactminer.RepositoryIntelligence.repo_intelligence_user import collect_user_additions
from artifactminer.RepositoryIntelligence.activity_classifier import classify_commit_activities

additions = collect_user_additions("/path/to/repo", "dev@example.com")
activities = classify_commit_activities(additions)

print(f"Code: {activities['code']['percentage']}%")
print(f"Tests: {activities['test']['percentage']}%")
print(f"Docs: {activities['docs']['percentage']}%")
print(f"Config: {activities['config']['percentage']}%")
```

---

### `print_activity_summary(activity_summary)`

**Description:** Pretty-prints an activity summary dictionary in a formatted table.

**Parameters:**
- `activity_summary` (dict): Output from `classify_commit_activities()`

**Returns:** None

**Side Effects:** Prints formatted table to stdout

**Example:**
```python
from artifactminer.RepositoryIntelligence.activity_classifier import classify_commit_activities, print_activity_summary

activities = classify_commit_activities(additions)
print_activity_summary(activities)

# Output:
# Activity    Commits    Lines Added     Percentage
# --------------------------------------------------
# code        45         1250            62
# test        12         380             19
# docs        8          220             11
# config      5          150             8
# design      0          0               0
```

---

## framework_detector.py

Framework and library detection system that analyzes dependency files across multiple programming languages.

### `detect_frameworks(repo_path)`

**Description:** Main entry point for framework detection. Scans repository dependency files and detects frameworks/libraries across Python, JavaScript, Java, and Go ecosystems.

**Parameters:**
- `repo_path` (str): Path to the repository

**Returns:** `List[str]` - Unique list of detected framework names

**Scanned Files:**
- **Python**: `requirements.txt`, `pyproject.toml`, `Pipfile`, `setup.py`
- **JavaScript/TypeScript**: `package.json`
- **Java**: `pom.xml`, `build.gradle`, `build.gradle.kts`
- **Go**: `go.mod`

**Example:**
```python
from artifactminer.RepositoryIntelligence.framework_detector import detect_frameworks

frameworks = detect_frameworks("/path/to/repo")
print(f"Detected frameworks: {', '.join(frameworks)}")
# Output: "Detected frameworks: React, FastAPI, Spring Boot, Express.js"
```

---

### `detect_python_frameworks(repo_path)`

**Description:** Detects Python frameworks by scanning Python-specific dependency files.

**Parameters:**
- `repo_path` (str): Path to repository

**Returns:** `List[str]` - List of detected Python frameworks

**Example:**
```python
from artifactminer.RepositoryIntelligence.framework_detector import detect_python_frameworks

frameworks = detect_python_frameworks("/path/to/python/project")
# Returns: ["FastAPI", "Django", "SQLAlchemy", ...]
```

---

### `detect_javascript_frameworks(repo_path)`

**Description:** Detects JavaScript/TypeScript frameworks by parsing `package.json` dependencies.

**Parameters:**
- `repo_path` (str): Path to repository

**Returns:** `List[str]` - List of detected JavaScript frameworks

**Example:**
```python
from artifactminer.RepositoryIntelligence.framework_detector import detect_javascript_frameworks

frameworks = detect_javascript_frameworks("/path/to/js/project")
# Returns: ["React", "Express.js", "Next.js", ...]
```

---

### `detect_java_frameworks(repo_path)`

**Description:** Detects Java frameworks by scanning Maven and Gradle build files.

**Parameters:**
- `repo_path` (str): Path to repository

**Returns:** `List[str]` - List of detected Java frameworks

**Example:**
```python
from artifactminer.RepositoryIntelligence.framework_detector import detect_java_frameworks

frameworks = detect_java_frameworks("/path/to/java/project")
# Returns: ["Spring Boot", "Hibernate", "JUnit", ...]
```

---

### `detect_go_frameworks(repo_path)`

**Description:** Detects Go frameworks by parsing `go.mod` file.

**Parameters:**
- `repo_path` (str): Path to repository

**Returns:** `List[str]` - List of detected Go frameworks

**Example:**
```python
from artifactminer.RepositoryIntelligence.framework_detector import detect_go_frameworks

frameworks = detect_go_frameworks("/path/to/go/project")
# Returns: ["Gin", "Echo", "GORM", ...]
```

---

## Data Classes

### `RepoStats`

Repository-level statistics dataclass returned by `getRepoStats()`.

**Fields:**
- `project_name` (str): Name of the repository
- `project_path` (str): Full path to repository
- `is_collaborative` (bool): Whether multiple contributors exist
- `Languages` (List[str]): File extensions found
- `language_percentages` (List[float]): Percentage of each language
- `primary_language` (str): Most common language
- `first_commit` (datetime): Oldest commit timestamp
- `last_commit` (datetime): Newest commit timestamp
- `total_commits` (int): Total commit count
- `frameworks` (List[str]): Detected frameworks

---

### `UserRepoStats`

User-specific statistics dataclass returned by `getUserRepoStats()`.

**Fields:**
- `project_name` (str): Repository name
- `project_path` (str): Repository path
- `first_commit` (datetime): User's first commit
- `last_commit` (datetime): User's last commit
- `total_commits` (int): User's commit count
- `userStatspercentages` (float): User's contribution percentage
- `commitFrequency` (float): Average commits per week
- `commitActivities` (dict): Activity breakdown by type

---

## Type Aliases

### `Pathish`

Type alias for path-like objects: `Union[os.PathLike, str]`

Accepts both string paths and `pathlib.Path` objects.

---

## Complete Workflow Example

Here's how to use the Repository Intelligence module in a complete workflow:

```python
from artifactminer.db.database import SessionLocal
from artifactminer.RepositoryIntelligence.repo_intelligence_main import getRepoStats, saveRepoStats
from artifactminer.RepositoryIntelligence.repo_intelligence_user import getUserRepoStats, saveUserRepoStats, generate_summaries_for_ranked
from artifactminer.RepositoryIntelligence.repo_intelligence_AI import set_user_consent

# Step 1: Set user consent for AI features
set_user_consent("full")

# Step 2: Analyze repository
repo_path = "/path/to/my/project"
repo_stats = getRepoStats(repo_path)
saveRepoStats(repo_stats)

print(f"Analyzed {repo_stats.project_name}")
print(f"Primary Language: {repo_stats.primary_language}")
print(f"Frameworks: {', '.join(repo_stats.frameworks)}")

# Step 3: Analyze user contributions
user_email = "developer@example.com"
user_stats = getUserRepoStats(repo_path, user_email)
saveUserRepoStats(user_stats)

print(f"\nUser contributed {user_stats.userStatspercentages:.1f}% of commits")
print(f"Commit frequency: {user_stats.commitFrequency:.2f} commits/week")
print(f"Activity breakdown:")
for activity, stats in user_stats.commitActivities.items():
    print(f"  {activity}: {stats['percentage']}%")

# Step 4: Generate AI summaries for top projects
db = SessionLocal()
try:
    summaries = generate_summaries_for_ranked(db, top=3)
    print("\nTop Project Summaries:")
    for summary in summaries:
        print(f"\n{summary['project_name']}:")
        print(summary['summary'])
finally:
    db.close()
```

---

## Notes

- All functions that interact with Git repositories will raise `ValueError` if the path is not a valid Git repository
- Email validation uses the `email_validator` library and will raise `EmailNotValidError` for invalid emails
- Database operations use SQLAlchemy sessions and automatically handle commits/rollbacks
- AI features require user consent to be set to "full" via `set_user_consent()`
- Framework detection relies on the `FRAMEWORK_DEPENDENCIES_BY_ECOSYSTEM` mapping in `artifactminer.mappings`

---

**Module Owner:** Evan/van-cpu  
**Last Updated:** November 2025
