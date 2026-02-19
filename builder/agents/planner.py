"""
Planner Agent
Converts user prompt into a structured project plan.
"""

import json
import re
from builder.llm import get_llm
from builder.states import Plan, File, AgentPhase
from builder.prompts import planner_prompt


def parse_plan_from_error(error_message: str):
    """Attempt to parse Plan from a failed_generation error."""
    try:
        match = re.search(
            r"<function=Plan>(\{.*?\})</function>", error_message, re.DOTALL
        )
        if match:
            json_str = match.group(1).replace('\\"', '"')
            data = json.loads(json_str)

            files = []
            for f in data.get("files", []):
                files.append(
                    File(
                        path=f.get("path", ""),
                        purpose=f.get("purpose", ""),
                        dependencies=f.get("dependencies", []),
                    )
                )

            return Plan(
                name=data.get("name", "Project"),
                description=data.get("description", ""),
                techstack=data.get("techstack", ""),
                features=data.get("features", []),
                files=files,
                architecture_notes=data.get("architecture_notes", ""),
            )
    except Exception as e:
        print(f"Failed to parse plan from error: {e}")
    return None


def planner_agent(state: dict) -> dict:
    """
    Planner Agent: Converts user prompt into a structured Plan.
    """
    user_prompt = state.get("user_prompt", "")

    if not user_prompt:
        return {
            "current_phase": AgentPhase.FAILED,
            "status": "FAILED",
            "errors": ["No user prompt provided"],
        }

    prompt = planner_prompt(user_prompt)
    llm = get_llm("planning")

    plan = None

    try:
        response = llm.with_structured_output(Plan).invoke(prompt)
        if response is not None:
            plan = response

    except Exception as e:
        error_str = str(e)

        if "failed_generation" in error_str:
            print("Attempting to parse plan from error...")
            plan = parse_plan_from_error(error_str)

    if plan is None:
        return {
            "current_phase": AgentPhase.FAILED,
            "status": "FAILED",
            "errors": ["Failed to create project plan"],
        }

    print(f"\n{'='*50}")
    print("PLAN CREATED")
    print(f"{'='*50}")
    print(f"Project: {plan.name}")
    print(f"Tech Stack: {plan.techstack}")
    print(f"Features: {len(plan.features)}")
    print(f"Files: {len(plan.files)}")
    print(f"{'='*50}\n")

    return {
        "user_prompt": user_prompt,
        "plan": plan,
        "current_phase": AgentPhase.PLANNING,
        "status": "planned",
    }
