"""
Architect Agent
Breaks down the plan into detailed implementation tasks.
"""

import json
import re
from agent.llm import get_llm
from agent.states import Plan, TaskPlan, ImplementationTask, AgentPhase
from agent.prompts import architect_prompt


def parse_failed_generation(error_message: str):
    """
    Attempt to parse the task plan from a failed_generation error.
    """
    try:
        match = re.search(r'<function=TaskPlan>(\{.*?\})</function>', error_message, re.DOTALL)
        
        if match:
            json_str = match.group(1)
            json_str = json_str.replace('\\"', '"')
            json_str = json_str.replace('\\n', '\n')
            json_str = json_str.replace('\\<', '<')
            json_str = json_str.replace('\\/', '/')
            
            data = json.loads(json_str)
            
            steps = []
            for step_data in data.get("implementation_steps", []):
                step = ImplementationTask(
                    filepath=step_data.get("filepath", ""),
                    task_description=step_data.get("task_description", ""),
                    dependencies=step_data.get("dependencies", []),
                    expected_exports=step_data.get("expected_exports", []),
                    priority=step_data.get("priority", 0)
                )
                steps.append(step)
            
            return TaskPlan(implementation_steps=steps)
    
    except Exception as e:
        print(f"Failed to parse failed_generation: {e}")
    
    return None


def create_fallback_task_plan(plan: Plan) -> TaskPlan:
    """Create a basic task plan from plan files."""
    fallback_steps = []
    
    priority_map = {
        '.json': 0,
        '.html': 1,
        '.css': 2,
        '.js': 3,
        '.py': 1,
        '.md': 4,
    }
    
    for i, file in enumerate(plan.files):
        ext = '.' + file.path.split('.')[-1] if '.' in file.path else ''
        priority = priority_map.get(ext, i)
        
        fallback_steps.append(ImplementationTask(
            filepath=file.path,
            task_description=f"""Create the file {file.path} for the {plan.name} project.

Purpose: {file.purpose}

Tech Stack: {plan.techstack}

Project Features to implement:
{chr(10).join('- ' + f for f in plan.features)}

Create a complete, working implementation. Include all necessary code.
""",
            dependencies=[f.path for f in plan.files[:i]],
            expected_exports=[],
            priority=priority
        ))
    
    fallback_steps.sort(key=lambda x: x.priority)
    return TaskPlan(implementation_steps=fallback_steps)


def architect_agent(state: dict) -> dict:
    """
    Architect Agent: Creates detailed TaskPlan from Plan.
    """
    plan = state.get("plan")
    
    if plan is None:
        return {
            "current_phase": AgentPhase.FAILED,
            "status": "FAILED",
            "errors": ["No plan provided to architect"]
        }
    
    prompt = architect_prompt(plan.model_dump_json())
    llm = get_llm("architect")
    
    task_plan = None
    
    try:
        response = llm.with_structured_output(TaskPlan).invoke(prompt)
        
        if response is not None:
            task_plan = response
            task_plan.plan = plan
            task_plan.implementation_steps.sort(key=lambda x: x.priority)
        
    except Exception as e:
        error_str = str(e)
        
        if "failed_generation" in error_str:
            print("Attempting to parse response from error...")
            task_plan = parse_failed_generation(error_str)
            
            if task_plan:
                task_plan.plan = plan
                task_plan.implementation_steps.sort(key=lambda x: x.priority)
    
    if task_plan is None:
        print("Using fallback: creating basic task plan from file list...")
        task_plan = create_fallback_task_plan(plan)
        task_plan.plan = plan
    
    print(f"\n{'='*50}")
    print("ARCHITECTURE CREATED")
    print(f"{'='*50}")
    print(f"Implementation Steps: {len(task_plan.implementation_steps)}")
    for i, step in enumerate(task_plan.implementation_steps, 1):
        print(f"  {i}. {step.filepath}")
    print(f"{'='*50}\n")
    
    return {
        "plan": plan,
        "task_plan": task_plan,
        "current_phase": AgentPhase.ARCHITECTING,
        "status": "architected"
    }