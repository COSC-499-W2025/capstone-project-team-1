from artifactminer.local_llm.generation.schemas import ProjectFacts


def test_project_facts_accepts_description_alias_and_string_lists() -> None:
    facts = ProjectFacts.model_validate(
        {
            "project_name": "artifact-miner",
            "project_type": "cli tool",
            "description": "CLI for mining project artifacts into resume facts.",
            "technologies": "Python\nFastAPI\nSQLite",
            "highlights": "- Built pipeline orchestration\n- Added local setup checks",
            "evidence": "README.md\nsrc/artifactminer/api/main.py",
        }
    )

    assert facts.summary == "CLI for mining project artifacts into resume facts."
    assert facts.technologies == ["Python", "FastAPI", "SQLite"]
    assert facts.highlights == [
        "Built pipeline orchestration",
        "Added local setup checks",
    ]
    assert facts.evidence == ["README.md", "src/artifactminer/api/main.py"]


def test_project_facts_derives_summary_from_highlights_when_missing() -> None:
    facts = ProjectFacts.model_validate(
        {
            "project_name": "artifact-miner",
            "project_type": "api service",
            "highlights": ["Built automatic database bootstrap"],
        }
    )

    assert facts.summary == "Built automatic database bootstrap"
