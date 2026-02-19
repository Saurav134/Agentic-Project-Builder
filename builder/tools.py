"""
Tools for the Agentic Project Builder
File operations, command execution, and utility tools.
"""

import os
import pathlib
import subprocess
from typing import Tuple
from langchain_core.tools import tool
from dotenv import load_dotenv

load_dotenv()


PROJECT_ROOT = pathlib.Path(
    os.getenv("PROJECT_OUTPUT_DIR", "generated_project")
).resolve()


def get_project_root() -> pathlib.Path:
    """Get the project root path."""
    return PROJECT_ROOT


def safe_path_for_project(path: str) -> pathlib.Path:
    """
    Ensure the path is within the project root to prevent directory traversal attacks.
    """

    if pathlib.Path(path).is_absolute():
        path = pathlib.Path(path).name

    p = (PROJECT_ROOT / path).resolve()

    try:
        p.relative_to(PROJECT_ROOT.resolve())
    except ValueError:
        raise ValueError(
            f"Security Error: Attempt to access path outside project root: {path}"
        )

    return p


def init_project_root() -> str:
    """Initialize the project root directory."""
    PROJECT_ROOT.mkdir(parents=True, exist_ok=True)
    return str(PROJECT_ROOT)


@tool
def write_file(path: str, content: str) -> str:
    """
    Writes content to a file at the specified path within the project root.
    Creates parent directories if they don't exist.

    Args:
        path: Relative path to the file within the project
        content: Content to write to the file

    Returns:
        Confirmation message with the file path
    """
    try:
        p = safe_path_for_project(path)
        p.parent.mkdir(parents=True, exist_ok=True)

        with open(p, "w", encoding="utf-8") as f:
            f.write(content)

        return f"SUCCESS: Wrote {len(content)} characters to {path}"
    except Exception as e:
        return f"ERROR: Failed to write to {path}: {str(e)}"


@tool
def read_file(path: str) -> str:
    """
    Reads content from a file at the specified path within the project root.

    Args:
        path: Relative path to the file within the project

    Returns:
        The file content, or empty string if file doesn't exist
    """
    try:
        p = safe_path_for_project(path)

        if not p.exists():
            return ""

        with open(p, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"ERROR: Failed to read {path}: {str(e)}"


@tool
def get_current_directory() -> str:
    """
    Returns the current project root directory path.

    Returns:
        The absolute path to the project root
    """
    return str(PROJECT_ROOT)


@tool
def list_files(directory: str = ".") -> str:
    """
    Lists all files in the specified directory within the project root.

    Args:
        directory: Relative path to the directory (default: project root)

    Returns:
        Newline-separated list of file paths, or error message
    """
    try:
        p = safe_path_for_project(directory)

        if not p.exists():
            return f"Directory does not exist: {directory}"

        if not p.is_dir():
            return f"ERROR: {directory} is not a directory"

        files = []
        for f in p.rglob("*"):
            if f.is_file():
                try:
                    rel_path = f.relative_to(PROJECT_ROOT)
                    files.append(str(rel_path))
                except ValueError:
                    pass

        if not files:
            return "No files found in directory."

        return "\n".join(sorted(files))
    except Exception as e:
        return f"ERROR: Failed to list files: {str(e)}"


@tool
def file_exists(path: str) -> bool:
    """
    Checks if a file exists at the specified path.

    Args:
        path: Relative path to check

    Returns:
        True if file exists, False otherwise
    """
    try:
        p = safe_path_for_project(path)
        return p.exists() and p.is_file()
    except:
        return False


@tool
def create_directory(path: str) -> str:
    """
    Creates a directory at the specified path.

    Args:
        path: Relative path for the directory

    Returns:
        Confirmation message
    """
    try:
        p = safe_path_for_project(path)
        p.mkdir(parents=True, exist_ok=True)
        return f"SUCCESS: Created directory {path}"
    except Exception as e:
        return f"ERROR: Failed to create directory {path}: {str(e)}"


@tool
def run_command(cmd: str, timeout: int = 30) -> str:
    """
    Runs a shell command in the project directory.

    Args:
        cmd: Command to execute
        timeout: Maximum execution time in seconds

    Returns:
        Command output or error message
    """
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        output_parts = []
        if result.stdout:
            output_parts.append(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            output_parts.append(f"STDERR:\n{result.stderr}")

        status = (
            "SUCCESS"
            if result.returncode == 0
            else f"FAILED (code {result.returncode})"
        )
        output_parts.insert(0, f"STATUS: {status}")

        return "\n".join(output_parts)
    except subprocess.TimeoutExpired:
        return f"ERROR: Command timed out after {timeout} seconds"
    except Exception as e:
        return f"ERROR: Failed to execute command: {str(e)}"


@tool
def validate_python_syntax(path: str) -> str:
    """
    Validates Python syntax of a file.

    Args:
        path: Path to the Python file

    Returns:
        Validation result
    """
    try:
        p = safe_path_for_project(path)
        if not p.exists():
            return f"ERROR: File does not exist: {path}"

        result = subprocess.run(
            ["python", "-m", "py_compile", str(p)], capture_output=True, text=True
        )

        if result.returncode == 0:
            return f"SUCCESS: {path} has valid Python syntax"
        else:
            return f"SYNTAX ERROR in {path}:\n{result.stderr}"
    except Exception as e:
        return f"ERROR: Validation failed: {str(e)}"


@tool
def validate_json_syntax(path: str) -> str:
    """
    Validates JSON syntax of a file.

    Args:
        path: Path to the JSON file

    Returns:
        Validation result
    """
    import json

    try:
        p = safe_path_for_project(path)
        if not p.exists():
            return f"ERROR: File does not exist: {path}"

        with open(p, "r") as f:
            json.load(f)

        return f"SUCCESS: {path} has valid JSON syntax"
    except json.JSONDecodeError as e:
        return f"JSON SYNTAX ERROR in {path}: {str(e)}"
    except Exception as e:
        return f"ERROR: Validation failed: {str(e)}"


def get_all_project_files() -> dict[str, str]:
    """
    Get all files in the project with their contents.
    Not a tool - used internally by agents.

    Returns:
        Dictionary mapping file paths to their contents
    """
    files = {}

    if not PROJECT_ROOT.exists():
        return files

    for file_path in PROJECT_ROOT.rglob("*"):
        if file_path.is_file():
            try:
                rel_path = str(file_path.relative_to(PROJECT_ROOT))
                with open(file_path, "r", encoding="utf-8") as f:
                    files[rel_path] = f.read()
            except Exception:
                pass

    return files


def get_project_context_summary(
    max_files: int = 10, max_chars_per_file: int = 3000
) -> str:
    """
    Get a summary of the project context for LLM consumption.
    Increased char limit so JS can see full HTML element IDs.
    """
    files = get_all_project_files()

    if not files:
        return "No files in project yet."

    summaries = []
    for i, (path, content) in enumerate(files.items()):
        if i >= max_files:
            summaries.append(f"... and {len(files) - max_files} more files")
            break

        truncated = content[:max_chars_per_file]
        if len(content) > max_chars_per_file:
            truncated += "\n... (truncated)"

        summaries.append(f"### {path}\n```\n{truncated}\n```")

    return "\n\n".join(summaries)


ALL_TOOLS = [
    write_file,
    read_file,
    get_current_directory,
    list_files,
    file_exists,
    create_directory,
    run_command,
    validate_python_syntax,
    validate_json_syntax,
]

CODER_TOOLS = [
    write_file,
    read_file,
    list_files,
    get_current_directory,
    file_exists,
]
