# Quick Command Reference

## Install Dependencies

```bash
uv sync --dev
```

## Ensure Ollama Models are Available

```bash
ollama pull llama3.2:1b
ollama pull llama3.2:3b
ollama pull qwen3:1.7b
ollama pull qwen3:4b-q4_K_M
```

## Run Benchmarks

### All tests (recommended)
```bash
uv run pytest tests/ollama/test_agent_loop.py -v -s
```

### Specific model
```bash
uv run pytest tests/ollama/test_agent_loop.py -v -s -k "llama3.2:1b"
```

### Specific test case
```bash
uv run pytest tests/ollama/test_agent_loop.py -v -s -k "multi_step_math"
```

### With longer timeout
```bash
uv run pytest tests/ollama/test_agent_loop.py -v -s --timeout=300
```

### Run quietly (less verbose)
```bash
uv run pytest tests/ollama/test_agent_loop.py -q
```

### Stop on first failure
```bash
uv run pytest tests/ollama/test_agent_loop.py -v -s -x
```
