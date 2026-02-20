"""
Fixer Agent
Fixes issues identified during code review.
"""

import re
from builder.llm import get_llm
from builder.states import ReviewState, CoderState, AgentPhase
from builder.tools import read_file, write_file


def extract_code_from_response(response_text: str, file_extension: str = ""):
    lang_map = {
        "js": ["javascript", "js"],
        "py": ["python", "py"],
        "html": ["html"],
        "css": ["css"],
        "json": ["json"],
    }
    patterns = []
    if file_extension in lang_map:
        for lang in lang_map[file_extension]:
            patterns.append(rf"```{lang}\n(.*?)```")
    patterns.extend(
        [
            r"```(?:html|css|javascript|js|python|json)?\n(.*?)```",
            r"```\n(.*?)```",
        ]
    )
    for pattern in patterns:
        matches = re.findall(pattern, response_text, re.DOTALL)
        if matches:
            return max(matches, key=len)
    return None


def clean_code_response(content: str) -> str:
    content = content.strip()
    if content.startswith("```"):
        lines = content.split("\n")
        start_idx = 1 if lines[0].startswith("```") else 0
        end_idx = len(lines)
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].strip() == "```":
                end_idx = i
                break
        content = "\n".join(lines[start_idx:end_idx])
    return content.strip()


def fixer_agent(state: dict) -> dict:
    review_state = state.get("review_state")
    coder_state = state.get("coder_state")
    task_plan = state.get("task_plan")
    plan = state.get("plan")
    user_prompt = state.get("user_prompt")

    if review_state is None:
        print("No review state provided, skipping fixes")
        return {
            "user_prompt": user_prompt,
            "plan": plan,
            "task_plan": task_plan,
            "coder_state": coder_state,
            "review_state": review_state,
            "current_phase": AgentPhase.FIXING,
            "status": "fixed",
        }

    print(f"\n{'='*50}")
    print("FIXING ISSUES")
    print(f"{'='*50}\n")

    files_to_fix = []
    skipped_files = []

    for review in review_state.reviews:
        if review.passed:
            skipped_files.append((review.filepath, "already passed"))
            continue
        if not review.issues or len(review.issues) == 0:
            skipped_files.append((review.filepath, "no specific issues to fix"))
            review.passed = True
            continue
        files_to_fix.append(review)

    if skipped_files:
        print("Skipped files:")
        for filepath, reason in skipped_files:
            print(f"  - {filepath}: {reason}")
        print()

    if not files_to_fix:
        print("No files with specific issues to fix!")
        print("All reviews have passed or have no actionable issues.")
        return {
            "user_prompt": user_prompt,
            "plan": plan,
            "task_plan": task_plan,
            "coder_state": coder_state,
            "review_state": review_state,
            "current_phase": AgentPhase.FIXING,
            "status": "fixed",
        }

    print(f"Files to fix: {len(files_to_fix)}")
    for review in files_to_fix:
        print(f"  - {review.filepath}: {len(review.issues)} issue(s)")
    print()

    llm = get_llm("fixer")
    fixed_files = []
    failed_fixes = []

    for review in files_to_fix:
        filepath = review.filepath
        issues = review.issues

        print(f"{'─'*40}")
        print(f"Fixing: {filepath}")
        print(f"Issues ({len(issues)}):")
        for i, issue in enumerate(issues, 1):
            severity = (
                issue.severity.value
                if hasattr(issue.severity, "value")
                else str(issue.severity)
            )
            print(f"  {i}. [{severity.upper()}] {issue.issue_type}")
            desc_preview = (
                issue.description[:80]
                if len(issue.description) > 80
                else issue.description
            )
            print(
                f"     Problem: {desc_preview}{'...' if len(issue.description) > 80 else ''}"
            )
            if issue.suggestion:
                sug_preview = (
                    issue.suggestion[:80]
                    if len(issue.suggestion) > 80
                    else issue.suggestion
                )
                print(
                    f"     Fix: {sug_preview}{'...' if len(issue.suggestion) > 80 else ''}"
                )

        try:
            content = read_file.invoke({"path": filepath})

            if not content or content.startswith("ERROR"):
                print(f"  ERROR: Cannot read file '{filepath}'")
                failed_fixes.append((filepath, "Cannot read file"))
                # continue

            original_length = len(content)
            file_ext = filepath.split(".")[-1].lower() if "." in filepath else ""

            issues_text = ""
            for i, issue in enumerate(issues, 1):
                severity = (
                    issue.severity.value
                    if hasattr(issue.severity, "value")
                    else str(issue.severity)
                )
                issues_text += f"{i}. [{severity.upper()}] {issue.issue_type}\n"
                issues_text += f"   Problem: {issue.description}\n"
                if issue.suggestion:
                    issues_text += f"   Suggested fix: {issue.suggestion}\n"
                issues_text += "\n"

            file_specific_instructions = ""
            if file_ext == "js":
                file_specific_instructions = """JAVASCRIPT RULES:
- This code runs in a WEB BROWSER, not Node.js
- Use document.getElementById(), querySelector(), addEventListener()
- Use localStorage for data persistence
- Do NOT use require(), import from node modules, or file system operations
- Ensure all element IDs match what's in the HTML file"""
            elif file_ext == "css":
                file_specific_instructions = """CSS RULES:
- Do NOT use backslash characters
- Ensure all selectors match elements in the HTML
- Use valid CSS syntax"""
            elif file_ext == "html":
                file_specific_instructions = """HTML RULES:
- Ensure proper DOCTYPE and structure
- All IDs should be unique
- Link CSS and JS files correctly"""
            elif file_ext == "py":
                file_specific_instructions = """PYTHON RULES:
- Include necessary imports
- Use proper indentation
- Handle exceptions appropriately"""

            fix_prompt = f"""Fix the following issues in this {file_ext.upper()} file.

FILE: {filepath}

CURRENT CODE:
{content}

ISSUES TO FIX:
{issues_text}

{file_specific_instructions}

INSTRUCTIONS:
1. Fix ALL the listed issues
2. Preserve all working functionality
3. Keep the same overall structure
4. Output ONLY the complete fixed code
5. Do NOT include explanations or markdown code blocks

OUTPUT THE FIXED CODE BELOW:"""

            response = llm.invoke(fix_prompt)
            fixed_content = response.content.strip()

            extracted = extract_code_from_response(fixed_content, file_ext)
            if extracted:
                fixed_content = extracted
            else:
                fixed_content = clean_code_response(fixed_content)

            if not fixed_content or len(fixed_content.strip()) < 10:
                print(f"  WARNING: Generated fix is empty or too short")
                print(f"  Keeping original file")
                failed_fixes.append((filepath, "Empty fix generated"))
                continue

            new_length = len(fixed_content)
            if new_length < original_length * 0.3:
                print(
                    f"  WARNING: Fix is much shorter than original ({new_length} vs {original_length} chars)"
                )
                print(f"  This might indicate lost content - keeping original")
                failed_fixes.append((filepath, "Fix too short, possible content loss"))
                continue

            if file_ext == "js":
                bad_patterns = ["require(", "module.exports", "fs.", "process."]
                for pattern in bad_patterns:
                    if pattern in fixed_content:
                        print(f"  WARNING: Fix contains Node.js pattern '{pattern}'")

            write_result = write_file.invoke(
                {"path": filepath, "content": fixed_content}
            )

            if "SUCCESS" in write_result:
                fixed_files.append(filepath)
                print(
                    f"  ✓ Successfully fixed ({original_length} -> {new_length} chars)"
                )
            else:
                print(f"  ✗ Failed to write: {write_result}")
                failed_fixes.append((filepath, f"Write failed: {write_result}"))

        except Exception as e:
            error_msg = str(e)[:100]
            print(f"  ✗ Exception: {error_msg}")
            failed_fixes.append((filepath, f"Exception: {error_msg}"))

    print(f"\n{'='*50}")
    print("FIX SUMMARY")
    print(f"{'='*50}")
    print(f"Successfully fixed: {len(fixed_files)}/{len(files_to_fix)} files")

    if fixed_files:
        print(f"\nFixed files:")
        for f in fixed_files:
            print(f"  ✓ {f}")

    if failed_fixes:
        print(f"\nFailed fixes:")
        for filepath, reason in failed_fixes:
            print(f"  ✗ {filepath}: {reason}")

    print(f"{'='*50}\n")

    return {
        "user_prompt": user_prompt,
        "plan": plan,
        "task_plan": task_plan,
        "coder_state": coder_state,
        "review_state": review_state,
        "current_phase": AgentPhase.FIXING,
        "status": "fixed",
    }
