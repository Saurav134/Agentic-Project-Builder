"""
Prompt Templates for all Agents
Contains carefully crafted prompts for each agent in the pipeline.
"""


def planner_prompt(user_prompt: str) -> str:
    """Generate the prompt for the Planner agent."""

    prompt = f"""You are an expert software architect. Convert the user's request into a project plan.

## User Request:
{user_prompt}

## Create a plan with:
1. name: Project name (string)
2. description: One-line description (string)  
3. techstack: Technologies to use (string)
4. features: List of features (array of strings)
5. files: List of files to create (array of objects with "path" and "purpose")
6. architecture_notes: Optional notes (string)

IMPORTANT:
You MUST return your answer using the Plan function.
Do NOT return plain text.
Do NOT explain anything.
Return ONLY the structured function call.

## Guidelines:
- For web apps: use HTML/CSS/JavaScript only (no config files)
- For Python apps: include requirements.txt if needed
- Keep file count minimal - only what's necessary
- Standard web app: index.html, style.css, script.js

Create a complete project plan.
"""
    return prompt


def architect_prompt(plan_json: str) -> str:
    """Generate the prompt for the Architect agent."""

    prompt = f"""You are a senior software architect. Break down this project plan into implementation tasks.

## Project Plan:
{plan_json}

## Create implementation_steps array where each step has:
1. filepath: File path (string)
2. task_description: Detailed instructions (string)
3. dependencies: Files that must exist first (array of strings)
4. expected_exports: What this file provides (array of strings)
5. priority: Order number, 0 = first (integer)

## Priority Order for web apps:
- 0: HTML files first
- 1: CSS files second  
- 2: JavaScript files last (so they can reference HTML element IDs)

## Priority Order for python code:
 - Create the requirement.txt at the end when all the project files are generated.
 - main.py should be created once all other python files are done.
 - For Python project, Always use python 3.13.3
## CRITICAL - NAMING CONSISTENCY:

In the HTML task description, you MUST define a "Element IDs" section that lists ALL interactive elements with their exact IDs. Use this format:

"Element IDs to use:
- [purpose]: id='[kebab-case-id]'
- [purpose]: id='[kebab-case-id]'
..."

Then in the JavaScript task description, reference these SAME IDs:

"Use these element IDs (from HTML):
- document.getElementById('[same-id-from-html]')
..."

The CSS task should also reference the same IDs and classes.

This ensures all three files use identical names.

## Naming Convention:
- Use kebab-case for IDs: 'user-input', 'submit-btn', 'output-display'
- Be descriptive but concise
- Keep names relevant to their purpose

Create detailed, consistent implementation tasks.
"""
    return prompt


def coder_system_prompt() -> str:
    """System prompt for the Coder agent."""

    prompt = """You are an expert developer generating code for a user's project.

## YOUR TOOLS:
- write_file(path, content): Save a file
- read_file(path): Read existing file

## CRITICAL RULES:

### 1. Code runs in USER'S environment
You generate code for browsers (HTML/CSS/JS) or Python - NOT your environment.

### 2. Browser JavaScript:
- Use localStorage for persistence
- Use document.getElementById(), addEventListener()
- NEVER use read_file() or write_file() in generated JS code
- Those are YOUR tools, not browser functions

### 3. Consistency Between Files:
- READ existing project files before writing
- Use EXACT SAME element IDs across HTML, CSS, JS
- If HTML has id="my-element", JS must use getElementById('my-element')
- If HTML has class="my-class", CSS must use .my-class

### 4. Quality:
- Complete, functional code
- Well-commented
- Modern best practices
- Visually appealing CSS with colors
"""
    return prompt


def coder_task_prompt(
    task_description: str,
    filepath: str,
    existing_content: str,
    project_context: str = "",
) -> str:
    """Generate the task-specific prompt for the Coder agent."""

    context_section = ""
    if project_context:
        context_section = f"""
## EXISTING PROJECT FILES - READ CAREFULLY:
{project_context}

IMPORTANT: Extract all element IDs and class names from existing files.
Your code MUST use the EXACT SAME IDs and class names.
"""

    file_ext = filepath.split(".")[-1].lower() if "." in filepath else ""

    specific_instructions = ""

    if file_ext == "js":
        specific_instructions = """
## JAVASCRIPT RULES:
- Runs in WEB BROWSER only
- Use document.getElementById(), querySelector(), addEventListener()
- Use localStorage for data persistence
- NEVER use read_file() or write_file() - those don't exist in browsers

## CONSISTENCY CHECK:
1. READ the HTML file in project context above
2. Find ALL element IDs in the HTML (look for id="...")
3. Use those EXACT IDs in your getElementById() calls
4. DO NOT invent new IDs - use what's in HTML
"""
    elif file_ext == "html":
        specific_instructions = """
## HTML RULES:
- Complete DOCTYPE, html, head, body structure
- Link CSS: <link rel="stylesheet" href="style.css">
- Link JS at body end: <script src="script.js"></script>

## ELEMENT IDS:
- Give every interactive element a unique id attribute
- Use kebab-case: id="user-input", id="submit-btn"
- These IDs will be used by JavaScript
"""
    elif file_ext == "css":
        specific_instructions = """
## CSS RULES:
- Make it COLORFUL and visually appealing
- Use gradients, shadows, animations, transitions
- Modern CSS: flexbox, grid
- NO backslash characters

## SELECTORS:
- READ the HTML file in project context
- Use the EXACT IDs from HTML: #element-id
- Use the EXACT classes from HTML: .class-name
"""
    elif file_ext == "py":
        specific_instructions = """
## PYTHON RULES:
- Include all necessary imports
- Add docstrings
- Handle exceptions
- Make it runnable
"""

    prompt = f"""Generate complete code for: {filepath}

## Task:
{task_description}

{specific_instructions}

{context_section}

## BEFORE WRITING:
1. If other files exist, READ them to find element IDs/classes
2. Ensure your code uses matching names
3. Generate COMPLETE, WORKING code

Use write_file("{filepath}", <code>) to save.
"""
    return prompt


def reviewer_prompt(filepath: str, content: str, task_description: str) -> str:
    """Generate the prompt for the Reviewer agent."""

    file_ext = filepath.split(".")[-1].lower() if "." in filepath else ""

    specific_checks = ""
    if file_ext == "js":
        specific_checks = """
## JavaScript Checks:
- FAIL if contains read_file() or write_file() calls
- FAIL if getElementById uses IDs not in HTML
- Uses proper browser APIs
- Has event listeners attached correctly
"""
    elif file_ext == "html":
        specific_checks = """
## HTML Checks:
- Has complete structure
- Links CSS and JS files
- Interactive elements have id attributes
"""
    elif file_ext == "css":
        specific_checks = """
## CSS Checks:
- No backslash characters
- Has actual colors (not just black/white)
- Selectors match HTML elements
"""

    prompt = f"""Review this code for quality and correctness.

## File: {filepath}

## Task:
{task_description}

## Code:
{content}

## Review Criteria:
1. Syntax correctness
2. Functionality - does it work?
3. Consistency - IDs match between files?
{specific_checks}

## Response Format:
- passed: boolean
- issues: array of problems
- overall_quality: 1-10
- summary: brief text

Be thorough but fair.
"""
    return prompt


def fixer_prompt(filepath: str, content: str, issues: list) -> str:
    """Generate the prompt for the Fixer agent."""

    issues_text = ""
    for issue in issues:
        if hasattr(issue, "description"):
            issues_text += f"- {issue.description}"
            if hasattr(issue, "suggestion"):
                issues_text += f": {issue.suggestion}"
            issues_text += "\n"
        else:
            issues_text += f"- {str(issue)}\n"

    if not issues_text.strip():
        issues_text = "- General improvements needed\n"

    file_ext = filepath.split(".")[-1].lower() if "." in filepath else ""

    specific_fixes = ""
    if file_ext == "js":
        specific_fixes = """
## JS Fix Rules:
- Replace any read_file()/write_file() with localStorage
- Ensure getElementById IDs match HTML
"""
    elif file_ext == "css":
        specific_fixes = """
## CSS Fix Rules:
- Remove backslash characters
- Add colors if too plain
"""

    prompt = f"""Fix the issues in this file.

## File: {filepath}

## Current Code:
{content}

## Issues:
{issues_text}

{specific_fixes}

Output the COMPLETE fixed code only. No markdown blocks. No explanations.
"""
    return prompt


def test_generator_prompt(plan_json: str, files_content: dict) -> str:
    """Generate the prompt for the Test Generator agent."""

    files_text = ""
    for path, content in files_content.items():
        truncated = content[:800] if len(content) > 800 else content
        files_text += f"\n### {path}\n```\n{truncated}\n```\n"

    prompt = f"""Create a test checklist for this project.

## Project:
{plan_json}

## Files:
{files_text}

Create a markdown checklist of manual tests to verify functionality.
Output only the markdown content.
"""
    return prompt


def finalizer_prompt(project_name: str, files_created: list, features: list) -> str:
    """Generate the prompt for the Finalizer agent."""

    files_str = ", ".join(files_created) if files_created else "None"
    features_str = ", ".join(features) if features else "None"

    prompt = f"""Create a README.md for this project.

## Project: {project_name}
## Files: {files_str}
## Features: {features_str}

Include:
1. Title and description
2. Features
3. How to run
4. File descriptions

Output markdown only.
"""
    return prompt
