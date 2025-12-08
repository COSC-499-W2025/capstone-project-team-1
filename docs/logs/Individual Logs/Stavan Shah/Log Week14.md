# logs - week-14

* Built a structured requirements data layer for the demo package (`demo/requirements.py`) that tracks all 20 project requirements with their implementation details.

* Created a `Requirement` dataclass with fields for id, short name, full description, status (FULLY MET/PARTIALLY MET/NOT MET), coverage percentage, how it's satisfied, and which demo sections demonstrate it.

* Defined all 20 requirements with detailed `how` fields explaining the implementation (e.g., "PUT /consent endpoint with 3-tier levels: full, no_llm, none").

* Added helper functions `get_requirement()` and `get_requirements_by_section()` for easy lookup, plus a `demonstrated_requirements` set to track which requirements have been shown during the demo.

* Fixed ZIP upload to return HTTP 422 instead of 400 for invalid file formats.

* This is PR 1/3 for the demo refactor - next PRs will add theme-styling and main-runner.

* Reviewed PRs including theme styling (#227), main runner (#229), repository health checker (#231), zip no mock (#232), and non-trivial test cases for /answers endpoint (#236).


| **task**                    | **status**     | **notes**      |
| --------------------------- | -------------- | -------------- |
| Build requirements data layer for demo | ■■ Done | Tracks all 20 reqs with compliance status and how each is met. |
| Add helper functions for requirement lookup | ■■ Done | get_requirement(), get_requirements_by_section(). |
| Fix ZIP upload error code | ■■ Done | Returns 422 instead of 400 for wrong format. |
