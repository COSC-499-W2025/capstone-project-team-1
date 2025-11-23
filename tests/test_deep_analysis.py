from pathlib import Path

from artifactminer.skills.deep_analysis import DeepRepoAnalyzer


class DummyRepoStat:
    def __init__(self, is_collaborative: bool = False, languages=None, frameworks=None):
        self.is_collaborative = is_collaborative
        self.Languages = languages or []
        self.languages = self.Languages
        self.frameworks = frameworks or []


def test_deep_repo_analyzer_surfaces_higher_order_signals_from_additions(tmp_path):
    repo_root = tmp_path / "deep_repo"
    repo_root.mkdir()
    (repo_root / "placeholder.py").write_text("# placeholder to mark python language\n")
    # User additions contain multiple deep patterns; baseline repo contents are irrelevant.
    additions = "\n".join(
        [
            "from collections import Counter, deque",
            "@dataclass",
            "class Foo: pass",
            "max_items = 10",
            "def handle(items):",
            "    try:",
            "        return Counter(items)",
            "    except Exception:",
            "        return {}",
            "with open('f') as f:",
            "    data = f.read()",
        ]
    )
    analyzer = DeepRepoAnalyzer(enable_llm=False)
    repo_stat = DummyRepoStat(is_collaborative=False, languages=["Python"])

    result = analyzer.analyze(
        repo_path=repo_root,
        repo_stat=repo_stat,
        user_email="user@example.com",
        user_contributions={"additions": additions},
        consent_level="none",
    )

    insight_map = {insight.title: insight.evidence for insight in result.insights}

    assert "Complexity awareness" in insight_map
    assert any("Resource caps or chunking" in ev for ev in insight_map["Complexity awareness"])

    assert "Data structure and optimization" in insight_map
    assert any("collections" in ev or "optimization" in ev for ev in insight_map["Data structure and optimization"])

    assert "Abstraction and encapsulation" in insight_map
    assert any("Dataclass" in ev or "Abstract" in ev for ev in insight_map["Abstraction and encapsulation"])

    assert "Robustness and error handling" in insight_map
    assert any("exception" in ev.lower() or "context manager" in ev.lower() for ev in insight_map["Robustness and error handling"])


def test_deep_repo_analyzer_does_not_credit_existing_code_without_additions(tmp_path):
    repo_root = tmp_path / "existing_repo"
    repo_root.mkdir()
    # Existing repo code that should not be credited to the user.
    (repo_root / "module.py").write_text("@dataclass\nclass Existing:\n    pass\n")

    # User only adds a simple limit, no abstraction patterns.
    additions = "max_rows = 10\n"

    analyzer = DeepRepoAnalyzer(enable_llm=False)
    repo_stat = DummyRepoStat(is_collaborative=False, languages=["Python"])

    result = analyzer.analyze(
        repo_path=repo_root,
        repo_stat=repo_stat,
        user_email="user@example.com",
        user_contributions={"additions": additions},
        consent_level="none",
    )

    insight_titles = {insight.title for insight in result.insights}
    assert "Complexity awareness" in insight_titles  # user-added limit
    assert "Abstraction and encapsulation" not in insight_titles  # came only from existing code, not user additions
