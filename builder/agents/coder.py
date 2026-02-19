"""
Coder Agent
Implements the actual code files based on task descriptions.
"""

import re
import json
from langgraph.prebuilt import create_react_agent

from builder.llm import get_llm
from builder.states import TaskPlan, CoderState, AgentPhase
from builder.prompts import coder_system_prompt, coder_task_prompt
from builder.tools import (
    CODER_TOOLS,
    read_file,
    write_file,
    get_project_context_summary,
)


def extract_and_execute_tool_call(error_message: str) -> bool:
    """
    Extract tool call from failed_generation error and execute it manually.
    """
    try:
        match = re.search(
            r"<function=write_file\s*(\{.+?\})>", error_message, re.DOTALL
        )

        if match:
            json_str = match.group(1)
            json_str = json_str.replace('\\"', '"')
            json_str = json_str.replace("\\n", "\n")
            json_str = json_str.replace("\\t", "\t")

            try:
                data = json.loads(json_str)
                path = data.get("path", "")
                content = data.get("content", "")
            except json.JSONDecodeError:
                path_match = re.search(r'"path"\s*:\s*"([^"]+)"', json_str)
                content_match = re.search(
                    r'"content"\s*:\s*"(.+)"', json_str, re.DOTALL
                )

                if path_match and content_match:
                    path = path_match.group(1)
                    content = content_match.group(1)
                    content = content.replace("\\n", "\n")
                    content = content.replace("\\t", "\t")
                    content = content.replace('\\"', '"')
                else:
                    return False

            if path and content:
                result = write_file.invoke({"path": path, "content": content})
                print(f"   Manually wrote file: {path}")
                return "SUCCESS" in result or "Wrote" in result

        return False

    except Exception as e:
        print(f"   Failed to extract tool call: {e}")
        return False


def extract_code_from_response(response_text: str):
    """Extract code from response text."""
    patterns = [
        r"```(?:html|css|javascript|js|python|json)?\n(.*?)```",
        r"```\n(.*?)```",
    ]

    for pattern in patterns:
        matches = re.findall(pattern, response_text, re.DOTALL)
        if matches:
            return max(matches, key=len)

    return None


def coder_agent(state: dict) -> dict:
    """
    Coder Agent: Implements files based on the task plan.
    """
    task_plan = state.get("task_plan")
    plan = state.get("plan")

    if task_plan is None:
        return {
            "current_phase": AgentPhase.FAILED,
            "status": "FAILED",
            "errors": ["No task plan provided to coder"],
        }

    coder_state = state.get("coder_state")

    if coder_state is None:
        coder_state = CoderState(
            task_plan=task_plan, current_step_idx=0, completed_files=[], failed_files=[]
        )

    steps = coder_state.task_plan.implementation_steps

    if coder_state.current_step_idx >= len(steps):
        print("\nAll coding tasks completed!")
        return {
            "plan": plan,
            "task_plan": task_plan,
            "coder_state": coder_state,
            "current_phase": AgentPhase.CODING,
            "status": "coded",
        }

    current_task = steps[coder_state.current_step_idx]

    print(f"\n{'='*50}")
    print(f"CODING: Step {coder_state.current_step_idx + 1}/{len(steps)}")
    print(f"{'='*50}")
    print(f"File: {current_task.filepath}")
    print(f"{'='*50}\n")

    file_written = False
    llm = get_llm("coding")

    try:
        existing_content = read_file.invoke({"path": current_task.filepath})
        if existing_content.startswith("ERROR"):
            existing_content = ""

        project_context = get_project_context_summary(
            max_files=5, max_chars_per_file=300
        )

        system_prompt = coder_system_prompt()
        user_prompt = coder_task_prompt(
            task_description=current_task.task_description,
            filepath=current_task.filepath,
            existing_content=existing_content,
            project_context=project_context,
        )

        react_agent = create_react_agent(llm, CODER_TOOLS)

        try:
            result = react_agent.invoke(
                {
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ]
                }
            )
            file_written = True

        except Exception as react_error:
            error_str = str(react_error)

            if "failed_generation" in error_str:
                print("   Tool call format error, attempting manual extraction...")
                file_written = extract_and_execute_tool_call(error_str)

            if not file_written:
                print("   Using direct generation fallback...")

                fallback_prompt = f"""Generate the complete code for: {current_task.filepath}

Task: {current_task.task_description}

CRITICAL RULES:
- For .js files: This is BROWSER JavaScript, NOT Node.js
  - Use localStorage for data storage
  - Use document.getElementById(), addEventListener()
  - DO NOT use read_file() or write_file() - those don't exist in browsers
  
- For .css files: Make it colorful and modern
  - Use gradients, shadows, animations
  - NO backslash characters
  
- For .html files: Complete valid HTML5
  - Include proper DOCTYPE, head, body
  - Link CSS: <link rel="stylesheet" href="style.css">
  - Link JS: <script src="script.js"></script>

Output ONLY the raw code. No explanations. No markdown code blocks.
"""

                try:
                    fallback_response = llm.invoke(fallback_prompt)
                    content = fallback_response.content

                    extracted = extract_code_from_response(content)
                    if extracted:
                        content = extracted

                    content = content.strip()
                    if content.startswith("```"):
                        lines = content.split("\n")
                        if len(lines) > 2:
                            content = "\n".join(lines[1:-1])

                    if content:
                        write_result = write_file.invoke(
                            {"path": current_task.filepath, "content": content}
                        )
                        file_written = "SUCCESS" in write_result
                        if file_written:
                            print(f"   File written via fallback method")

                except Exception as fallback_error:
                    print(f"   Fallback also failed: {fallback_error}")

        if file_written:
            coder_state.completed_files.append(current_task.filepath)
            print(f"Completed: {current_task.filepath}")
        else:
            coder_state.failed_files.append(current_task.filepath)
            print(f"Failed: {current_task.filepath} (will continue with other files)")

    except Exception as e:
        print(f"Error coding {current_task.filepath}: {str(e)}")
        coder_state.failed_files.append(current_task.filepath)

    coder_state.current_step_idx += 1

    if coder_state.current_step_idx >= len(steps):
        return {
            "plan": plan,
            "task_plan": task_plan,
            "coder_state": coder_state,
            "current_phase": AgentPhase.CODING,
            "status": "coded",
        }
    else:
        return {
            "plan": plan,
            "task_plan": task_plan,
            "coder_state": coder_state,
            "current_phase": AgentPhase.CODING,
            "status": "coding",
        }
