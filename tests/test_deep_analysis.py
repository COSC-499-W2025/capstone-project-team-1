from pathlib import Path
from copy import deepcopy

import pytest

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
    # User additions contain multiple deep patterns AND base patterns; baseline repo contents are irrelevant.
    additions = "\n".join(
        [
            "from collections import Counter, deque",
            "import logging",  # Add logging (base pattern)
            "@dataclass",
            "class Foo: pass",
            "class CustomError(Exception): pass",  # Add custom exception (base pattern)
            "max_items = 10",
            "def handle(items):",
            "    logging.info('Processing items')",  # Use logging
            "    try:",
            "        return Counter(items)",
            "    except CustomError:",
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
    skill_names = {s.skill for s in result.skills}

    # Verify base patterns are detected
    assert "Logging" in skill_names, "Base pattern: Logging should be detected"
    assert "Error Handling" in skill_names, "Base pattern: Error Handling should be detected"

    assert "Complexity awareness" in insight_map
    assert any("Resource caps or chunking" in ev for ev in insight_map["Complexity awareness"])

    assert "Data structure and optimization" in insight_map
    assert any("collections" in ev or "optimization" in ev for ev in insight_map["Data structure and optimization"])

    assert "Abstraction and encapsulation" in insight_map
    assert any("Dataclass" in ev or "Abstract" in ev for ev in insight_map["Abstraction and encapsulation"])

    # Verify robustness insight includes BOTH base and deep patterns
    assert "Robustness and error handling" in insight_map
    robustness_evidence = insight_map["Robustness and error handling"]

    # Should have multiple pieces of evidence (both base and deep patterns contribute)
    assert len(robustness_evidence) >= 2, "Robustness should have evidence from multiple skills"

    # Verify that base pattern skills contributed (check skill names, not evidence text)
    base_robustness_skills = {"Logging", "Error Handling"}
    deep_robustness_skills = {"Context Management", "Exception Design"}

    detected_base = [s for s in base_robustness_skills if s in skill_names]
    detected_deep = [s for s in deep_robustness_skills if s in skill_names]

    assert len(detected_base) > 0, f"At least one base robustness skill should be detected: {base_robustness_skills}"
    assert len(detected_deep) > 0, f"At least one deep robustness skill should be detected: {deep_robustness_skills}"


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


def test_validation_catches_invalid_insight_rules(monkeypatch):
    """Verify that _validate_insight_rules catches references to non-existent skills."""
    # Temporarily add an invalid rule (use deepcopy to avoid mutating nested sets)
    original_rules = deepcopy(DeepRepoAnalyzer._INSIGHT_RULES)

    try:
        # Add a rule referencing a skill that doesn't exist
        DeepRepoAnalyzer._INSIGHT_RULES["Invalid insight"] = {
            "skills": {"NonExistentSkill", "AnotherFakeSkill"},
            "why": "This should fail validation",
        }

        # Should raise ValueError on initialization
        with pytest.raises(ValueError, match="references unknown skills"):
            DeepRepoAnalyzer(enable_llm=False)

    finally:
        # Restore original rules
        DeepRepoAnalyzer._INSIGHT_RULES = original_rules
