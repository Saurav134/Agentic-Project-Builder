"""
Finalizer Agent
Creates final documentation and wraps up the project.
"""

import re
from datetime import datetime

from agent.llm import get_llm
from agent.states import Plan, CoderState, AgentPhase
from agent.tools import list_files, get_project_root, write_file


def finalizer_agent(state: dict) -> dict:
    """
    Finalizer Agent: Creates README and final documentation.
    """
    plan = state.get("plan")
    user_prompt = state.get("user_prompt", "")

    print(f"\n{'='*50}")
    print("FINALIZING PROJECT")
    print(f"{'='*50}\n")

    if plan is None:
        print("Plan object:", plan)
        print("Plan features:", getattr(plan, "features", None))

        project_path = str(get_project_root())
        return {
            "current_phase": AgentPhase.COMPLETE,
            "status": "DONE",
            "final_summary": "Project completed",
            "project_path": project_path,
            "completed_at": datetime.now(),
        }
    print("Plan object:", plan)
    print("Plan features:", getattr(plan, "features", None))

    files_list = list_files.invoke({"directory": "."})
    files_created = []
    for f in files_list.split("\n"):
        f = f.strip()
        if f and not f.startswith("ERROR") and not f.startswith("No files"):
            files_created.append(f)

    llm = get_llm("planning")

    try:
        features_str = ", ".join(plan.features)
        files_str = ", ".join(files_created)

        readme_prompt = f"""Create a README.md file for this project. Output only the markdown content.

Project: {plan.name}
Description: {plan.description}
Tech Stack: {plan.techstack}
Features: {features_str}
Files: {files_str}

Include:
- Project title and description
- Features list
- How to run (open index.html in browser for web projects)
- File structure
"""

        response = llm.invoke(readme_prompt)
        readme_content = response.content.strip()
        print("README : ", readme_content)
        if readme_content.startswith("```"):
            match = re.search(
                r"```(?:markdown|md)?\n(.*?)```", readme_content, re.DOTALL
            )
            if match:
                readme_content = match.group(1)

        write_result = write_file.invoke(
            {"path": "README.md", "content": readme_content}
        )

        if "SUCCESS" in write_result:
            print("Created README.md")
            if "README.md" not in files_created:
                files_created.append("README.md")

    except Exception as e:
        print(f"Failed to create README: {str(e)}")

    project_path = str(get_project_root())

    features_lines = ""
    for f in plan.features:
        features_lines += f"  - {f}\n"

    files_lines = ""
    for f in files_created[:15]:
        files_lines += f"  - {f}\n"

    if len(files_created) > 15:
        files_lines += f"  ... and {len(files_created) - 15} more files\n"

    final_summary = f"""
{'='*60}
PROJECT GENERATION COMPLETE
{'='*60}

Project: {plan.name}
Location: {project_path}
Tech Stack: {plan.techstack}

Features:
{features_lines}
Files Created:
{files_lines}
Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

To run: Open index.html in your web browser

{'='*60}
"""

    print(final_summary)

    return {
        "current_phase": AgentPhase.COMPLETE,
        "status": "DONE",
        "final_summary": final_summary,
        "project_path": project_path,
        "completed_at": datetime.now(),
    }
