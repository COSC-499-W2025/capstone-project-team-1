from fastapi.testclient import TestClient
from pathlib import Path



def test_analyze_repo(client):
    root = Path(__file__).resolve().parents[2]
    user_email = "ecrowl01@student.ubc.ca"
    response = client.post("/repos/analyze", params={"repo_path": root, "user_email": user_email})
    assert response.status_code == 200
    data = response.json()
    assert "repo_stats" in data
    assert "user_stats" in data
    assert isinstance(data["user_stats"]["total_commits"], int)
    formatted_user_stats = f"UserRepoStat(total_commits={data['user_stats']['total_commits']}, user_commit_percentage={data['user_stats']['userStatspercentages']})"
    print("User Repo Stats:")
    print(formatted_user_stats)
