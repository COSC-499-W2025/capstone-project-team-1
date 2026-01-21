import os
from pathlib import Path
from ollama import chat, ChatResponse

# Global base directory - set at runtime
BASE_DIR: str = ""


def resolve_path(path: str) -> str:
    """Resolve a path relative to BASE_DIR if not absolute."""
    if os.path.isabs(path):
        return path
    return os.path.join(BASE_DIR, path)


def list_directory(path: str) -> str:
    """List all files and folders in a directory.

    Args:
        path: The path to the directory (can be relative to base directory or absolute).

    Returns:
        A string containing the names of all files and folders in the directory,
        with folders marked with a trailing slash.
    """
    try:
        full_path = resolve_path(path)
        entries = os.listdir(full_path)
        result = []
        for entry in sorted(entries):
            entry_path = os.path.join(full_path, entry)
            if os.path.isdir(entry_path):
                result.append(f"{entry}/")
            else:
                result.append(entry)
        return "\n".join(result) if result else "Directory is empty"
    except FileNotFoundError:
        return f"Error: Directory '{path}' not found"
    except PermissionError:
        return f"Error: Permission denied for '{path}'"


def read_file(path: str) -> str:
    """Read and return the contents of a file.

    Args:
        path: The path to the file (can be relative to base directory or absolute).

    Returns:
        The contents of the file as a string.
    """
    try:
        full_path = resolve_path(path)
        with open(full_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return f"Error: File '{path}' not found"
    except PermissionError:
        return f"Error: Permission denied for '{path}'"
    except UnicodeDecodeError:
        return f"Error: File '{path}' is not a text file or has encoding issues"


def get_file_info(path: str) -> str:
    """Get metadata information about a file.

    Args:
        path: The path to the file (can be relative to base directory or absolute).

    Returns:
        A string containing the file size in bytes and the file extension.
    """
    try:
        full_path = resolve_path(path)
        stat = os.stat(full_path)
        size = stat.st_size
        extension = Path(full_path).suffix or "(no extension)"
        is_dir = os.path.isdir(full_path)
        return f"Size: {size} bytes\nExtension: {extension}\nIs directory: {is_dir}"
    except FileNotFoundError:
        return f"Error: Path '{path}' not found"
    except PermissionError:
        return f"Error: Permission denied for '{path}'"


available_functions = {
    "list_directory": list_directory,
    "read_file": read_file,
    "get_file_info": get_file_info,
}

SYSTEM_PROMPT = """You are a code repository explorer. You MUST use tools to explore directories and read files.

IMPORTANT: 
- Always call tools. Never explain what you will do - just do it.
- Use relative paths like "README.md", "main.py", "utils/helpers.py" (paths are resolved automatically)
- To list root directory, use path "."

Steps:
1. Call list_directory with "." to see files in the root
2. Call read_file on each important file (README.md, .py files)
3. If you see subdirectories (marked with /), explore them with list_directory
4. Read at least 4-5 files before summarizing

When you have read enough files to understand the codebase, provide a detailed summary of:
- What the repository does
- Key components and their purposes
- Technologies/frameworks used"""

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    BASE_DIR = os.path.join(script_dir, "mock_repo")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "Explore this repository. Start by calling list_directory with path '.'"},
    ]

    print(f"Starting exploration of: {BASE_DIR}\n")
    print("=" * 60)

    MAX_ITERATIONS = 15
    iteration = 0

    while iteration < MAX_ITERATIONS:
        iteration += 1
        print(f"\n--- Iteration {iteration}/{MAX_ITERATIONS} ---")
        response: ChatResponse = chat(
            model="qwen3:4b",
            messages=messages,
            tools=[list_directory, read_file, get_file_info],
            think=True,
        )
        messages.append(response.message)

        if response.message.thinking:
            thinking_preview = response.message.thinking[:500] + "..." if len(response.message.thinking) > 500 else response.message.thinking
            print(f"Thinking: {thinking_preview}")
        if response.message.content:
            print(f"Content: {response.message.content}")

        if response.message.tool_calls:
            for tc in response.message.tool_calls:
                func_name = tc.function.name
                func_args = tc.function.arguments
                print(f"\nTool Call: {func_name}({func_args})")

                if func_name in available_functions:
                    result = available_functions[func_name](**func_args)
                    print(f"Result:\n{result}")
                    messages.append({
                        "role": "tool",
                        "tool_name": func_name,
                        "content": str(result),
                    })
                else:
                    error_msg = f"Unknown function: {func_name}"
                    print(error_msg)
                    messages.append({
                        "role": "tool",
                        "tool_name": func_name,
                        "content": error_msg,
                    })
        else:
            print("\n" + "=" * 60)
            print("Exploration complete!")
            break

    if iteration >= MAX_ITERATIONS:
        print("\n" + "=" * 60)
        print("Max iterations reached. Forcing summary.")
