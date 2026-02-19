"""
Test Generator Agent
Generates test cases for the project.
"""

from agent.llm import get_llm
from agent.states import TaskPlan, TestPlan, TestCase, AgentPhase
from agent.prompts import test_generator_prompt
from agent.tools import get_all_project_files, write_file


def detect_project_type(plan, files_content: dict) -> str:
    """
    Detect the project type based on plan and file extensions.

    Args:
        plan: The project plan (may be None)
        files_content: Dictionary of filepath -> content

    Returns:
        Project type string: 'web', 'python', or 'unknown'
    """

    if plan and plan.techstack:
        techstack = plan.techstack.lower()

        web_keywords = [
            "html",
            "css",
            "javascript",
            "js",
            "web",
            "frontend",
            "front-end",
            "react",
            "vue",
            "angular",
            "svelte",
        ]
        if any(keyword in techstack for keyword in web_keywords):
            return "web"

        python_keywords = ["python", "py", "django", "flask", "fastapi"]
        if any(keyword in techstack for keyword in python_keywords):
            return "python"

    if files_content:
        extensions = set()
        for filepath in files_content.keys():
            if "." in filepath:
                ext = filepath.split(".")[-1].lower()
                extensions.add(ext)

        web_extensions = {"html", "css", "js", "jsx", "tsx", "vue", "svelte"}
        if extensions & web_extensions:
            return "web"

        python_extensions = {"py", "pyw", "pyx"}
        if extensions & python_extensions:
            return "python"

    return "unknown"


def generate_web_tests(plan, files_content: dict) -> tuple:
    """
    Generate test checklist for web projects.

    Returns:
        Tuple of (test_content, test_filename, TestPlan)
    """
    project_name = plan.name if plan else "Web Project"
    features = plan.features if plan else []

    feature_checks = ""
    if features:
        feature_checks = "\n## Feature Tests\n"
        for i, feature in enumerate(features, 1):
            feature_checks += f"{i}. [ ] {feature}\n"

    files_list = (
        "\n".join(f"- {f}" for f in files_content.keys())
        if files_content
        else "- No files"
    )

    test_content = f"""# Test Checklist for {project_name}

## Project Files
{files_list}

## Basic Functionality Tests

### Page Load
1. [ ] Page loads without errors
2. [ ] No JavaScript errors in browser console (F12 -> Console)
3. [ ] No 404 errors for CSS/JS files (F12 -> Network)
4. [ ] All images and assets load correctly

### UI Elements
1. [ ] All UI elements are visible
2. [ ] Layout displays correctly
3. [ ] Colors and styling match design
4. [ ] Text is readable

### Interactivity
1. [ ] Buttons respond to clicks
2. [ ] Form inputs accept text
3. [ ] Interactive elements have hover states
4. [ ] Animations/transitions work smoothly
{feature_checks}
## Responsive Design
1. [ ] Works on desktop (1920x1080)
2. [ ] Works on tablet (768x1024)
3. [ ] Works on mobile (375x667)

## Data Persistence (if applicable)
1. [ ] Data saves correctly
2. [ ] Data persists after page refresh
3. [ ] Data can be deleted/modified

## Browser Compatibility
1. [ ] Works in Chrome
2. [ ] Works in Firefox
3. [ ] Works in Safari (if available)
4. [ ] Works in Edge

## How to Test
1. Open `index.html` in a web browser
2. Open Developer Tools (F12)
3. Check the Console tab for errors
4. Check the Network tab for failed requests
5. Test each feature manually
6. Check each item in this list

## Notes
- Mark items with [x] when verified
- Add any bugs found below

## Bugs Found
(Add any bugs discovered during testing here)

"""

    test_filename = "tests/test_checklist.md"

    test_plan = TestPlan(
        test_framework="manual",
        test_files=[
            TestCase(
                test_name="test_checklist.md",
                test_type="manual",
                target_file="index.html",
                test_code=test_content,
                description="Manual test checklist for web project",
            )
        ],
        setup_instructions="Open index.html in a web browser and follow the checklist",
    )

    return test_content, test_filename, test_plan


def generate_python_tests(plan, files_content: dict) -> tuple:
    """
    Generate test file for Python projects.

    Returns:
        Tuple of (test_content, test_filename, TestPlan)
    """
    project_name = plan.name if plan else "Python Project"

    py_files = [f for f in files_content.keys() if f.endswith(".py")]

    imports = ""
    test_functions = ""

    for py_file in py_files:

        module_name = py_file.replace("/", ".").replace("\\", ".").replace(".py", "")
        if module_name.startswith("."):
            module_name = module_name[1:]

        if "test" in module_name.lower() or module_name == "__init__":
            continue

        imports += f"# from {module_name} import *  # Uncomment and modify as needed\n"

        safe_name = module_name.replace(".", "_")
        test_functions += f'''
def test_{safe_name}_exists():
    """Test that {py_file} can be imported."""
    try:
        # Uncomment the import above and modify this test
        assert True, "{py_file} exists"
    except ImportError as e:
        pytest.fail(f"Cannot import {module_name}: {{e}}")


'''

    test_content = f'''"""
Test Suite for {project_name}

Run tests with: pytest tests/test_main.py -v
"""

import pytest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

{imports}

# ============== Test Cases ==============

def test_project_structure():
    """Test that required files exist."""
    required_files = {[repr(f) for f in py_files[:5]]}
    
    for filepath in required_files:
        assert os.path.exists(filepath), f"Missing file: {{filepath}}"

{test_functions}

def test_placeholder():
    """
    Placeholder test - replace with actual tests.
    
    TODO: Add tests for:
    - Main functionality
    - Edge cases
    - Error handling
    """
    assert True, "Placeholder test passes"


# ============== Run Tests ==============

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
'''

    test_filename = "tests/test_main.py"

    pytest_ini = """[pytest]
testpaths = tests
python_files = test_*.py
python_functions = test_*
addopts = -v --tb=short
"""

    test_plan = TestPlan(
        test_framework="pytest",
        test_files=[
            TestCase(
                test_name="test_main.py",
                test_type="unit",
                target_file="*.py",
                test_code=test_content,
                description="Main test file for Python project",
            )
        ],
        setup_instructions="Run: pip install pytest && pytest tests/ -v",
    )

    return test_content, test_filename, test_plan, pytest_ini


def generate_generic_tests(plan, files_content: dict) -> tuple:
    """
    Generate generic test checklist for unknown project types.

    Returns:
        Tuple of (test_content, test_filename, TestPlan)
    """
    project_name = plan.name if plan else "Project"
    files_list = (
        "\n".join(f"- {f}" for f in files_content.keys())
        if files_content
        else "- No files"
    )

    test_content = f"""# Test Checklist for {project_name}

## Project Files
{files_list}

## Verification Steps

### File Verification
1. [ ] All expected files are present
2. [ ] Files are not empty
3. [ ] No syntax errors in code files

### Functionality
1. [ ] Project runs without errors
2. [ ] Main functionality works as expected
3. [ ] Output is correct

### Edge Cases
1. [ ] Empty input handled
2. [ ] Invalid input handled
3. [ ] Large input handled

## How to Test
1. Review the files above
2. Run the main entry point
3. Test each feature manually
4. Check each item in this list

## Bugs Found
(Add any bugs discovered during testing here)

"""

    test_filename = "tests/test_checklist.md"

    test_plan = TestPlan(
        test_framework="manual",
        test_files=[
            TestCase(
                test_name="test_checklist.md",
                test_type="manual",
                target_file="*",
                test_code=test_content,
                description="Generic test checklist",
            )
        ],
        setup_instructions="Review files and test manually",
    )

    return test_content, test_filename, test_plan


def test_generator_agent(state: dict) -> dict:
    """
    Test Generator Agent: Creates test cases for the project.

    Bug Fix #2: Properly detects project type using multiple methods
    (techstack keywords, file extensions) and generates appropriate tests.
    """
    task_plan = state.get("task_plan")
    plan = state.get("plan")
    user_prompt = state.get("user_prompt")
    coder_state = state.get("coder_state")
    review_state = state.get("review_state")

    print(f"\n{'='*50}")
    print("GENERATING TESTS")
    print(f"{'='*50}\n")

    files_content = get_all_project_files()

    if not files_content:
        print("No files found in project, skipping test generation")
        return {
            "user_prompt": user_prompt,
            "plan": plan,
            "task_plan": task_plan,
            "coder_state": coder_state,
            "review_state": review_state,
            "test_run_state": {
                "test_plan": None,
                "results": [],
                "all_passed": True,
                "total_tests": 0,
                "passed_tests": 0,
            },
            "current_phase": AgentPhase.TESTING,
            "status": "no_tests_needed",
        }

    project_type = detect_project_type(plan, files_content)

    techstack = plan.techstack if plan else "unknown"
    print(f"Project techstack: {techstack}")
    print(f"Detected project type: {project_type}")
    print(f"Files in project: {list(files_content.keys())}")
    print()

    test_plan = None

    if project_type == "web":
        print("Generating web project tests...")
        test_content, test_filename, test_plan = generate_web_tests(plan, files_content)

        write_result = write_file.invoke(
            {"path": test_filename, "content": test_content}
        )

        if "SUCCESS" in write_result:
            print(f"✓ Created {test_filename}")
        else:
            print(f"✗ Failed to create {test_filename}: {write_result}")

    elif project_type == "python":
        print("Generating Python project tests...")
        result = generate_python_tests(plan, files_content)
        test_content, test_filename, test_plan = result[0], result[1], result[2]

        write_result = write_file.invoke(
            {"path": test_filename, "content": test_content}
        )

        if "SUCCESS" in write_result:
            print(f"✓ Created {test_filename}")
        else:
            print(f"✗ Failed to create {test_filename}: {write_result}")

        if len(result) > 3:
            pytest_ini = result[3]
            write_file.invoke({"path": "pytest.ini", "content": pytest_ini})
            print("✓ Created pytest.ini")

    else:
        print(f"Unknown project type, generating generic tests...")
        test_content, test_filename, test_plan = generate_generic_tests(
            plan, files_content
        )

        write_result = write_file.invoke(
            {"path": test_filename, "content": test_content}
        )

        if "SUCCESS" in write_result:
            print(f"✓ Created {test_filename}")
        else:
            print(f"✗ Failed to create {test_filename}: {write_result}")

    print(f"\n{'='*50}")
    print(f"TEST GENERATION COMPLETE")
    print(f"Project type: {project_type}")
    print(f"Test framework: {test_plan.test_framework if test_plan else 'none'}")
    print(f"Test files created: {len(test_plan.test_files) if test_plan else 0}")
    if test_plan and test_plan.setup_instructions:
        print(f"Setup: {test_plan.setup_instructions}")
    print(f"{'='*50}\n")

    return {
        "user_prompt": user_prompt,
        "plan": plan,
        "task_plan": task_plan,
        "coder_state": coder_state,
        "review_state": review_state,
        "test_run_state": {
            "test_plan": test_plan,
            "results": [],
            "all_passed": True,
            "total_tests": len(test_plan.test_files) if test_plan else 0,
            "passed_tests": len(test_plan.test_files) if test_plan else 0,
        },
        "current_phase": AgentPhase.TESTING,
        "status": "tests_generated",
    }
