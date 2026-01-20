"""Reusable agent loop for Ollama models with tool calling."""

from dataclasses import dataclass
from typing import Callable, Dict, List, Any, Optional, Union
from ollama import chat, ChatResponse
import time


@dataclass
class AgentLoopResult:
    """Result from an agent loop execution."""

    model: str
    final_answer: str
    total_time_seconds: float
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    tool_calls_made: int
    is_correct: Optional[bool] = None  # Set by test harness


class AgentLoop:
    """Reusable agent loop for Ollama models with tool calling."""

    def __init__(
        self,
        model: str,
        tools: List[Callable],
        available_functions: Dict[str, Callable],
        max_iterations: int = 10,
    ):
        """
        Initialize the agent loop.

        Args:
            model: The Ollama model name to use
            tools: List of tool functions to make available
            available_functions: Dict mapping function names to callables
            max_iterations: Maximum number of agent loop iterations
        """
        self.model = model
        self.tools = tools
        self.available_functions = available_functions
        self.max_iterations = max_iterations

    def run(self, messages: List[Dict[str, Any]]) -> AgentLoopResult:
        """
        Execute the agent loop and return metrics.

        Args:
            messages: Initial conversation messages

        Returns:
            AgentLoopResult with timing, token counts, and final answer
        """
        messages_copy: List[Any] = [
            msg.copy() for msg in messages
        ]  # Don't mutate input
        start_time = time.perf_counter()
        total_prompt_tokens = 0
        total_completion_tokens = 0
        tool_calls_count = 0
        final_content = ""

        for _ in range(self.max_iterations):
            response: ChatResponse = chat(
                model=self.model,
                messages=messages_copy,
                tools=self.tools,
            )
            # Append the message object directly - Ollama handles it
            messages_copy.append(response.message)
            final_content = response.message.content or ""

            # Accumulate token counts (if available from Ollama response)
            if hasattr(response, "prompt_eval_count") and response.prompt_eval_count:
                total_prompt_tokens += response.prompt_eval_count
            if hasattr(response, "eval_count") and response.eval_count:
                total_completion_tokens += response.eval_count

            if response.message.tool_calls:
                for tc in response.message.tool_calls:
                    tool_calls_count += 1
                    if tc.function.name in self.available_functions:
                        result = self.available_functions[tc.function.name](
                            **tc.function.arguments
                        )
                        messages_copy.append(
                            {
                                "role": "tool",
                                "tool_name": tc.function.name,
                                "content": str(result),
                            }
                        )
            else:
                # No more tool calls, agent is done
                break

        elapsed = time.perf_counter() - start_time

        return AgentLoopResult(
            model=self.model,
            final_answer=final_content,
            total_time_seconds=elapsed,
            prompt_tokens=total_prompt_tokens,
            completion_tokens=total_completion_tokens,
            total_tokens=total_prompt_tokens + total_completion_tokens,
            tool_calls_made=tool_calls_count,
        )


# --- Tool definitions (used for standalone execution) ---
def add(a: int, b: int) -> int:
    """Add two numbers."""
    a = int(a) if isinstance(a, str) else a
    b = int(b) if isinstance(b, str) else b
    return a + b


def multiply(a: int, b: int) -> int:
    """Multiply two numbers."""
    a = int(a) if isinstance(a, str) else a
    b = int(b) if isinstance(b, str) else b
    return a * b


if __name__ == "__main__":
    # Example standalone usage
    available_functions = {
        "add": add,
        "multiply": multiply,
    }

    agent = AgentLoop(
        model="qwen3:1.7b",
        tools=[add, multiply],
        available_functions=available_functions,
    )

    messages = [{"role": "user", "content": "What is (11434+12341)*412?"}]
    result = agent.run(messages)

    print(f"Model: {result.model}")
    print(f"Answer: {result.final_answer}")
    print(f"Time: {result.total_time_seconds:.2f}s")
    print(f"Tokens: {result.total_tokens}")
    print(f"Tool calls: {result.tool_calls_made}")
