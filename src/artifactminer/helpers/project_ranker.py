import os
import subprocess
from pathlib import Path
from typing import List, Dict, Optional

def rank_projects(projects_dir: str, user_name: str = "Shlok Shah") -> List[Dict]:
    """
    Ranks projects in the given directory based on the user's contribution percentage.

    Args:
        projects_dir: Path to the directory containing project subdirectories.
        user_name: The name of the user to calculate contributions for.

    Returns:
        A list of dictionaries, each containing:
            - name: Project name (directory name)
            - score: User's contribution percentage (0-100)
            - total_commits: Total number of commits in the project
            - user_commits: Number of commits by the user
    """
    projects = []
    base_path = Path(projects_dir)

    if not base_path.exists() or not base_path.is_dir():
        return []

    for project_path in base_path.iterdir():
        if project_path.is_dir() and (project_path / ".git").exists():
            try:
                # Get commit counts per author
                # git shortlog -s -n --all
                # Output format: "   10  Author Name"
                output = subprocess.check_output(
                    ["git", "shortlog", "-s", "-n", "--all"],
                    cwd=str(project_path),
                    text=True,
                    stderr=subprocess.DEVNULL
                )

                total_commits = 0
                user_commits = 0

                for line in output.strip().split('\n'):
                    if not line.strip():
                        continue
                    
                    parts = line.strip().split('\t', 1)
                    if len(parts) != 2:
                        # Handle cases where split by tab might fail, though shortlog usually uses tab
                        # Fallback to splitting by first space if tab fails, but shortlog -s is reliable
                        parts = line.strip().split(maxsplit=1)
                    
                    if len(parts) == 2:
                        count = int(parts[0])
                        author = parts[1]
                        
                        total_commits += count
                        if author.lower() == user_name.lower():
                            user_commits += count

                score = (user_commits / total_commits * 100) if total_commits > 0 else 0.0

                projects.append({
                    "name": project_path.name,
                    "score": round(score, 2),
                    "total_commits": total_commits,
                    "user_commits": user_commits
                })

            except subprocess.CalledProcessError:
                # Skip if git command fails
                continue
            except Exception as e:
                print(f"Error processing {project_path.name}: {e}")
                continue

    # Sort by score descending
    projects.sort(key=lambda x: x["score"], reverse=True)
    return projects
