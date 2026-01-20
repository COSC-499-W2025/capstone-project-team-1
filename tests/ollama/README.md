# Ollama Agent Loop Benchmark Suite

This directory contains comprehensive benchmarking tests for the Ollama agent loop across multiple models.

## Overview

The benchmark suite tests how different Ollama models perform with tool calling capabilities. Each model is tested across multiple test cases with both cold start and warm inference runs to measure performance differences.

## Architecture

### Files

- **`test_agent_loop.py`**: Main test file with parametrized pytest tests
- **`conftest.py`**: Pytest configuration that displays a beautiful results table after tests complete
- **`../../src/artifactminer/helpers/ollama-agent.py`**: Refactored `AgentLoop` class used by tests

### Models Tested

The following models are benchmarked (removed gemma3 models as they don't support tool calling):

- `llama3.2:1b`
- `llama3.2:3b`
- `qwen3:1.7b`
- `qwen3:4b-q4_K_M`

### Test Cases

Each model is tested with the following scenarios:

1. **multi_step_math**: Complex calculation `(11434+12341)*412 = 9,787,500`
2. **simple_add**: Basic addition `42 + 58 = 100`
3. **simple_multiply**: Basic multiplication `25 * 4 = 100`
4. **chained_ops**: Multi-step reasoning `(100 + 200) * 3 = 900`

### Metrics Captured

For each test run, the following metrics are collected:

- **Time**: Execution time in seconds
- **Tokens**: Prompt tokens, completion tokens, and total tokens
- **Tool Calls**: Number of tool function calls made
- **Accuracy**: Whether the model produced the correct answer

## Setup

### Install Dependencies

```bash
# Install test dependencies using uv
uv sync --dev
```

This will install:
- `pytest` - Test framework
- `pytest-timeout` - Timeout support for long-running tests
- `rich` - Beautiful console output for results table

### Ensure Models are Available

Make sure you have the Ollama models pulled locally:

```bash
ollama pull llama3.2:1b
ollama pull llama3.2:3b
ollama pull qwen3:1.7b
ollama pull qwen3:4b-q4_K_M
```

## Running Tests

### Run All Benchmarks

```bash
# Run all models and test cases
uv run pytest tests/ollama/test_agent_loop.py -v -s
```

### Run Specific Model

```bash
# Test only llama3.2:1b
uv run pytest tests/ollama/test_agent_loop.py -v -s -k "llama3.2:1b"

# Test only qwen3 models
uv run pytest tests/ollama/test_agent_loop.py -v -s -k "qwen3"
```

### Run Specific Test Case

```bash
# Run only the multi-step math test
uv run pytest tests/ollama/test_agent_loop.py -v -s -k "multi_step_math"

# Run only simple operations
uv run pytest tests/ollama/test_agent_loop.py -v -s -k "simple"
```

### Run with Custom Timeout

```bash
# Override default 120s timeout
uv run pytest tests/ollama/test_agent_loop.py -v -s --timeout=180
```

## Understanding Results

After all tests complete, a summary table will be displayed:

```
🚀 Ollama Agent Loop Benchmark Results
┌─────────────────┬─────────────────┬──────┬──────────┬────────────┬───────────┬────────────┬────────┐
│ Model           │ Test Case       │ Run  │ Time (s) │ Prompt Tok │ Compl Tok │ Tool Calls │ Status │
├─────────────────┼─────────────────┼──────┼──────────┼────────────┼───────────┼────────────┼────────┤
│ llama3.2:1b     │ multi_step_math │ cold │    12.34 │       1234 │       456 │          2 │   ✓    │
│ llama3.2:1b     │ multi_step_math │ warm │     2.45 │       1234 │       456 │          2 │   ✓    │
│ ...             │ ...             │ ...  │      ... │        ... │       ... │        ... │   ...  │
└─────────────────┴─────────────────┴──────┴──────────┴────────────┴───────────┴────────────┴────────┘

Summary Statistics:
  llama3.2:1b: Avg cold=10.50s, warm=2.20s, speedup=4.77x
  llama3.2:3b: Avg cold=15.30s, warm=3.10s, speedup=4.94x
  qwen3:1.7b: Avg cold=8.20s, warm=1.80s, speedup=4.56x
  qwen3:4b-q4_K_M: Avg cold=12.10s, warm=2.50s, speedup=4.84x

Overall Accuracy: 32/32 (100.0%)
```

### Key Metrics

- **Cold vs Warm**: First run (cold) vs second run (warm) shows model loading overhead
- **Speedup**: Ratio of cold/warm time - higher is better
- **Status**: ✓ means correct answer, ✗ means incorrect
- **Accuracy**: Percentage of test runs that produced the correct answer

## Customization

### Adding New Test Cases

Edit `test_agent_loop.py` and add to the `TEST_CASES` list:

```python
TestCase(
    name="your_test_name",
    messages=[{"role": "user", "content": "Your question here?"}],
    expected_answer=42,
    validator=contains_number,
)
```

### Adding New Models

Edit the `OLLAMA_MODELS` list in `test_agent_loop.py`:

```python
OLLAMA_MODELS: List[str] = [
    "llama3.2:1b",
    "your-new-model:tag",
]
```

### Adding New Tools

Edit the tool definitions in both `test_agent_loop.py` and `ollama-agent.py`:

```python
def your_tool(param: int) -> int:
    """Your tool description."""
    return param * 2

AVAILABLE_FUNCTIONS = {
    "add": add,
    "multiply": multiply,
    "your_tool": your_tool,
}

TOOLS = [add, multiply, your_tool]
```

## Troubleshooting

### Timeout Errors

If tests timeout, increase the timeout:

```bash
uv run pytest tests/ollama/test_agent_loop.py -v -s --timeout=300
```

### Model Not Found

Ensure the model is pulled:

```bash
ollama pull model-name:tag
```

### Import Errors

The test uses `importlib` to handle the hyphenated filename `ollama-agent.py`. If you encounter import issues, ensure the path is correct.

## Notes

- Each test case runs twice per model (cold + warm) = 2 runs
- With 4 models and 4 test cases = 32 total test runs
- Total execution time will depend on your hardware and model sizes
- Token counts may show "N/A" if Ollama doesn't return token metrics for certain models
