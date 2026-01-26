import subprocess
import re
from pathlib import Path
from typing import Dict, List, Set


def _discover_git_projects(base_path: Path) -> Set[Path]:
    """Return all directories under base_path that contain a `.git` folder."""
    repo_dirs: Set[Path] = set()
    if not base_path.exists():
        return repo_dirs

    for git_dir in base_path.rglob(".git"):
        if git_dir.is_dir():
            repo_dirs.add(git_dir.parent)
    return repo_dirs


def rank_projects(projects_dir: str, user_email: str) -> List[Dict]:
    """
    Ranks projects in the given directory based on the user's contribution percentage,
    identified strictly by their email address.

    Args:
        projects_dir: Path to the directory containing project subdirectories.
        user_email: The email of the user to calculate contributions for.

    Returns:
        A list of dictionaries, each containing:
            - name: Project name (directory name)
            - score: User's contribution percentage (0-100)
            - total_commits: Total number of commits in the project
            - user_commits: Number of commits by the user
    """
    projects = []
    base_path = Path(projects_dir)
    target_email = user_email.lower().strip()

    if not base_path.exists() or not base_path.is_dir():
        return []

    repo_paths = _discover_git_projects(base_path)

    for project_path in repo_paths:
        try:
            # Get commit counts per author with email
            output = subprocess.check_output(
                ["git", "shortlog", "-s", "-n", "-e", "--all"],
                cwd=str(project_path),
                text=True,
                stderr=subprocess.DEVNULL,
                timeout=5,
            )

            total_commits = 0
            user_commits = 0

            for line in output.strip().split("\n"):
                if not line.strip():
                    continue

                parts = line.strip().split(maxsplit=1)
                if len(parts) < 2:
                    continue

                try:
                    count = int(parts[0])
                    rest = parts[1]

                    total_commits += count

                    email_match = re.search(r"<([^>]+)>", rest)
                    if email_match:
                        author_email = email_match.group(1).lower().strip()
                        if author_email == target_email:
                            user_commits += count

                except ValueError:
                    continue

            score = (user_commits / total_commits * 100) if total_commits else 0.0

            projects.append(
                {
                    "name": project_path.name,
                    "score": round(score, 2),
                    "total_commits": total_commits,
                    "user_commits": user_commits,
                }
            )

        except subprocess.CalledProcessError:
            continue
        except Exception as e:
            print(f"Error processing {project_path.name}: {e}")
            continue

    projects.sort(key=lambda x: x["score"], reverse=True)
    return projects
