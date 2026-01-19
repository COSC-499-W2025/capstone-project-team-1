Term 2 Week 2 (Jan 12 - Jan 18)

[Term 2 Week 1 (Jan 5 - Jan 11)](@docs/logs/Individual Logs/Shlok Shah/Week_15.md)

[Week 16](Week16.png)

Continuing from Week 15, I moved from developing on the application to researching local LLM options for the next phase and planning an architecture on how can we integrate local LLM as a service in our application.

### Coding tasks

- Explored Ollama, structured outputs (forcing JSON/schema-like responses), and which local model balances speed vs output quality.
- Researched `llama.cpp` and the Python bindings (`llama-cpp-python`) as another way to run local models.
- Built a small testbench (https://github.com/COSC-499-W2025/capstone-project-team-1/pull/290) to compare cold-start vs warm-start speed across 4 Ollama models (gemma3:4b, gemma3:1b, llama3.2:1b, llama3.2:3b).

### Testing or debugging tasks

- Dealt with an Alembic heads conflict that was briefly blocking work; followed the fix/merge and made sure tests still pass: https://github.com/COSC-499-W2025/capstone-project-team-1/pull/279.

### Reviewing or collaboration tasks

- PRs I reviewed (with what I asked for):
- https://github.com/COSC-499-W2025/capstone-project-team-1/pull/279 (Fix email validation and merge alembic heads)
  Asked for: use `validate_email(...).email` and avoid extra manual normalization; make sure the PR targets `development`.
- https://github.com/COSC-499-W2025/capstone-project-team-1/pull/281 (280 - add Async OpenAI calls)
  Asked for: reuse a single `AsyncOpenAI` client instead of creating one per call.
- https://github.com/COSC-499-W2025/capstone-project-team-1/pull/275 ([API] Scope analyze to selected dirs)
  Commented: tested the directory scoping flow and confirmed tests pass; approved.

### Plan for next week

- Continue the OpenTUI exploration and nail down the architecture for the local LLM service and decide between Ollama and llama-cpp-python.
- Work on general development/ housekeeping of the application

### Blockers

- Alembic heads conflict; addressed by merging the heads and validating tests still pass.

