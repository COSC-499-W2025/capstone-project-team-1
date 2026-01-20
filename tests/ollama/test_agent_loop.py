"""Simple benchmark: cold vs warm inference speeds for Ollama models."""

import pytest
from artifactminer.helpers.ollama_agent import AgentLoop

# Models to benchmark
MODELS = ["llama3.2:1b", "llama3.2:3b", "qwen3:1.7b", "qwen3:4b-q4_K_M"]


# Simple tools
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return int(a) + int(b)


def multiply(a: int, b: int) -> int:
    """Multiply two numbers."""
    return int(a) * int(b)


TOOLS = [add, multiply]
FUNCTIONS = {"add": add, "multiply": multiply}

# Test cases: (name, message, expected_answer)
TEST_CASES = [
    ("multi_step", "What is (11434+12341)*412?", 9787500),
    ("simple_add", "What is 42 + 58?", 100),
    ("simple_multiply", "What is 25 * 4?", 100),
    ("chained", "Add 100 and 200, then multiply by 3. What's the result?", 900),
]

# Store results for summary
RESULTS = []


@pytest.mark.timeout(600)
@pytest.mark.parametrize("model", MODELS)
@pytest.mark.parametrize("name,message,expected", TEST_CASES)
def test_benchmark(model, name, message, expected):
    """Run cold and warm inference, track time/success/accuracy."""
    agent = AgentLoop(model=model, tools=TOOLS, available_functions=FUNCTIONS)

    for run in ["cold", "warm"]:
        success, correct, time_s, tokens = False, False, 0.0, 0
        try:
            result = agent.run([{"role": "user", "content": message}])
            success = True
            time_s = result.total_time_seconds
            tokens = result.total_tokens
            correct = str(expected) in result.final_answer.replace(",", "")
        except:
            pass

        RESULTS.append((model, name, run, time_s, tokens, success, correct))
        status = "+" if success and correct else "-" if success else "E"
        print(
            f"{status} {model} | {name} | {run} | {time_s:.2f}s | {tokens}tok | ok={success} correct={correct}"
        )


def pytest_sessionfinish(session, exitstatus):
    """Print summary after all tests."""
    if not RESULTS:
        return

    print("\n\n=== SUMMARY ===")
    for model in MODELS:
        runs = [r for r in RESULTS if r[0] == model and r[5]]  # successful only
        if not runs:
            print(f"{model}: No successful runs")
            continue

        cold = [r[3] for r in runs if r[2] == "cold"]
        warm = [r[3] for r in runs if r[2] == "warm"]
        correct = len([r for r in RESULTS if r[0] == model and r[6]])
        total = len([r for r in RESULTS if r[0] == model])

        if cold and warm:
            avg_cold = sum(cold) / len(cold)
            avg_warm = sum(warm) / len(warm)
            speedup = avg_cold / avg_warm if avg_warm > 0 else 0
            print(
                f"{model}: cold={avg_cold:.2f}s warm={avg_warm:.2f}s speedup={speedup:.1f}x accuracy={correct}/{total}"
            )
