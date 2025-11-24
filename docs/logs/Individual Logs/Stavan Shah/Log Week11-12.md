# logs - week-11-12

## Week 11 (Reading Break)

* Set up Alembic migrations for database schema versioning so teammates don't need to delete db while testing PRs.
* Migrated existing database to Alembic with initial migration including all milestone 1 models.
* Added relationships between models and cascade behavior to foreign keys.
* Fixed migration constraint names to work properly with SQLite.
* Documented instructions on how to use Alembic for the team.

## Week 12

* Refactored mappings.py by extracting shared mappings and updating framework detector to use generic skill names with all dependencies included.

* Added database schema for UserProjectSkill, Proficiency, and Evidence tables to support skill tracking functionality.

* Built skill extraction engine with deep analysis for higher-order repo insights and enhanced DeepRepoAnalyzer robustness with validation.

* Removed git and file signals logic along with test cases, LLM refinement, and kit integration to simplify the engine.


| **task**                    | **status**     | **notes**      |
| --------------------------- | -------------- | -------------- |
| Add alembic migrations to db | ■■ Done | Completed during reading break. |
| Refactor mappings.py | ■■ Done | Extracted shared mappings and updated framework detector. |
| Add schema for user_project_skills and project_skills | ■■ Done | Added UserProjectSkill, Proficiency, and Evidence models. |
| Build skill extraction engine | ■■ Done | Added deep analysis and enhanced robustness. |
