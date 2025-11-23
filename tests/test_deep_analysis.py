from pathlib import Path

import git

from artifactminer.skills.deep_analysis import DeepRepoAnalyzer


class DummyRepoStat:
    def __init__(self, is_collaborative: bool = False, languages=None, frameworks=None):
        self.is_collaborative = is_collaborative
        self.Languages = languages or []
        self.languages = self.Languages
        self.frameworks = frameworks or []


def _seed_python_repo(tmp_path: Path) -> Path:
    repo_root = tmp_path / "deep_repo"
    repo_root.mkdir()
    (repo_root / "module.py").write_text(
        "\n".join(
            [
                "from collections import Counter, deque",
                "from dataclasses import dataclass",
                "import heapq",
                "",
                "max_items = 100",
                "chunk_size = 50",
                "sample_limit = 10",
                "",
                "@dataclass",
                "class Example:",
                "    value: int",
                "",
                "def process(items):",
                "    counts = Counter(items)",
                "    try:",
                "        return list(counts.keys())",
                "    except Exception:",
                "        return []",
            ]
        )
    )
    return repo_root


def test_deep_repo_analyzer_surfaces_higher_order_signals(tmp_path):
    repo_root = _seed_python_repo(tmp_path)
    analyzer = DeepRepoAnalyzer(enable_llm=False)
    repo_stat = DummyRepoStat(is_collaborative=False, languages=["Python"])

    result = analyzer.analyze(
        repo_path=repo_root,
        repo_stat=repo_stat,
        user_email="user@example.com",
        user_contributions={},
        consent_level="none",
    )

    assert result.skills, "baseline skills should still be produced"
    insight_map = {insight.title: insight.evidence for insight in result.insights}

    assert "Complexity awareness" in insight_map
    assert any("max_items" in ev or "chunk_size" in ev for ev in insight_map["Complexity awareness"])

    assert "Data structure choices" in insight_map
    assert any("Counter" in ev or "deque" in ev or "heapq" in ev for ev in insight_map["Data structure choices"])

    assert "Abstraction and encapsulation" in insight_map
    assert any("@dataclass" in ev or "class Example" in ev for ev in insight_map["Abstraction and encapsulation"])

    assert "Robustness and error handling" in insight_map
    assert any("try:" in ev or "except" in ev for ev in insight_map["Robustness and error handling"])


def test_deep_repo_analyzer_respects_user_scope(tmp_path):
    repo_root = tmp_path / "collab_deep_repo"
    repo_root.mkdir()
    repo = git.Repo.init(repo_root)

    target_actor = git.Actor("Target User", "target@example.com")
    other_actor = git.Actor("Other User", "other@example.com")

    # Other contributor adds their own file with signals that should be ignored.
    other_file = repo_root / "other.py"
    other_file.write_text("@dataclass\nclass Other:\n    pass\n")
    repo.index.add([str(other_file.relative_to(repo_root))])
    repo.index.commit("other commit", author=other_actor, committer=other_actor)

    # Target user adds content that should be considered.
    user_file = repo_root / "user.py"
    user_file.write_text("from collections import Counter\n\nmax_rows = 10\n\ndef f(x):\n    try:\n        return Counter(x)\n    except Exception:\n        return {}\n")
    repo.index.add([str(user_file.relative_to(repo_root))])
    repo.index.commit("user commit", author=target_actor, committer=target_actor)

    analyzer = DeepRepoAnalyzer(enable_llm=False)
    repo_stat = DummyRepoStat(is_collaborative=True)

    result = analyzer.analyze(
        repo_path=repo_root,
        repo_stat=repo_stat,
        user_email="target@example.com",
        user_contributions={},
        consent_level="none",
    )

    insight_map = {insight.title: insight.evidence for insight in result.insights}
    assert "Data structure choices" in insight_map
    assert any("user.py" in ev for ev in insight_map["Data structure choices"])
    assert all("other.py" not in ev for ev in insight_map["Data structure choices"])

    assert "Complexity awareness" in insight_map
    assert any("user.py" in ev for ev in insight_map["Complexity awareness"])
    assert all("other.py" not in ev for ev in insight_map["Complexity awareness"])
