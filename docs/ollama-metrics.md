# Ollama structured-output metrics

This document explains the metrics printed by the Ollama structured-output benchmarks and how to interpret them.

## Metrics

### Mirage rate (token-level novelty)
- What it measures: The share of output tokens that do not appear in the project snapshot and are not in a small stopword list.
- How it is computed:
  - Tokenize the model output (project name, one-liner, highlights, skills).
  - Count tokens not present in the snapshot and not in the stopword list.
  - Divide by total token count.
- Interpretation:
  - Lower is better.
  - High values suggest the model is introducing vocabulary not grounded in the snapshot.
- Limitations:
  - Surface-level heuristic only; paraphrases can look like mirages even when factual.

### Entity grounding rate
- What it measures: The share of entity-like tokens in the output that appear in the snapshot.
- How it is computed:
  - Tokenize output.
  - Keep tokens longer than 2 chars, not stopwords, and not purely numeric.
  - Count how many of these appear in the snapshot.
  - Divide by total entity-like tokens.
- Interpretation:
  - Higher is better.
  - High values suggest the model is reusing entities present in the snapshot.
- Limitations:
  - Token-based matching; synonyms or variants may not match.

### Redundancy rate
- What it measures: Duplicate items across highlights and skills.
- How it is computed:
  - Normalize each item to tokens, count duplicates.
  - Duplicates are counted as repeated occurrences beyond the first.
  - Divide by total items.
- Interpretation:
  - Lower is better.
  - High values indicate repetitive bullets or skill lists.

## OpenAI baseline comparison
The OpenAI comparison test prints deltas vs the OpenAI baseline. Example:
- `delta_mirage = model_mirage - openai_mirage`
  - Positive delta means worse (more mirage).
- `delta_entity_grounding = model_grounding - openai_grounding`
  - Positive delta means better grounding.
- `delta_redundancy = model_redundancy - openai_redundancy`
  - Positive delta means worse (more repetition).

## Model size and hardware guidance (rules of thumb)
These are rough, conservative estimates for running local LLMs. Actual requirements depend on quantization, context length, and backend.

- Parameter count is a rough proxy for memory use.
- As a quick heuristic, assume 1B parameters needs around 1 to 2 GB of RAM or VRAM.
- If running on GPU, you typically want the model to fit mostly in VRAM for best speed.
- If running on CPU, plan for extra system RAM beyond the model size to avoid swapping.

Examples:
- 1B model: ~1 to 2 GB RAM/VRAM.
- 3B model: ~3 to 6 GB RAM/VRAM.
- 8B model: ~8 to 16 GB RAM/VRAM.
- 13B model: ~13 to 26 GB RAM/VRAM.

For stable performance, add a buffer of 2 to 4 GB of system RAM beyond these estimates.
