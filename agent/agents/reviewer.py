"""
Reviewer Agent
Reviews generated code for quality, correctness, and best practices.
"""

import re
import json
from agent.llm import get_llm
from agent.states import (
    CoderState,
    ReviewState,
    CodeReview,
    CodeIssue,
    ReviewSeverity,
    AgentPhase,
)
from agent.prompts import reviewer_prompt
from agent.tools import read_file


def parse_review_from_error(error_str: str, filepath: str):
    try:
        match = re.search(
            r"<function=CodeReview>(\{.*?\})</function>", error_str, re.DOTALL
        )
        if match:
            json_str = match.group(1).replace('\\"', '"')
            data = json.loads(json_str)
            issues = []
            for issue_data in data.get("issues", []):
                severity_str = issue_data.get("severity", "medium").lower()
                try:
                    severity = ReviewSeverity(severity_str)
                except ValueError:
                    severity = ReviewSeverity.MEDIUM
                issues.append(
                    CodeIssue(
                        issue_type=issue_data.get("issue_type", "unknown"),
                        description=issue_data.get("description", ""),
                        suggestion=issue_data.get("suggestion", ""),
                        severity=severity,
                    )
                )
            return CodeReview(
                filepath=filepath,
                issues=issues,
                passed=data.get("passed", True),
                overall_quality=data.get("overall_quality", 7),
                summary=data.get("summary", ""),
            )
    except Exception as e:
        print(f"Failed to parse review: {e}")
    return None


def clean_review_response(text: str) -> str:
    """Remove markdown formatting from review response."""
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\|[^\n]+\|", "", text)
    text = re.sub(r"^\s*[-#]+\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_issues_from_response(response_text: str) -> list:
    """Try to extract specific issues from LLM response."""
    issues = []
    cleaned = clean_review_response(response_text)
    lines = cleaned.split("\n")

    for line in lines:
        line = line.strip()
        if not line or len(line) < 10:
            continue
        if line.upper().startswith("PASS") or line.upper().startswith("FAIL"):
            continue
        if line.startswith("Result:") or line.startswith("Issues"):
            continue
        if any(
            word in line.lower()
            for word in [
                "issue",
                "error",
                "missing",
                "incorrect",
                "should",
                "need",
                "fix",
                "add",
                "remove",
                "change",
            ]
        ):
            if len(line) > 15 and len(line) < 300:
                issues.append(line)

    return issues[:5]


def reviewer_agent(state: dict) -> dict:
    coder_state = state.get("coder_state")
    task_plan = state.get("task_plan")
    plan = state.get("plan")
    user_prompt = state.get("user_prompt")
    existing_review_state = state.get("review_state")
    print("PLAN IS :", plan)
    if coder_state is None:
        if task_plan is not None:
            coder_state = CoderState(
                task_plan=task_plan,
                current_step_idx=len(task_plan.implementation_steps),
                completed_files=[
                    step.filepath for step in task_plan.implementation_steps
                ],
                failed_files=[],
            )
        else:
            return {
                "user_prompt": user_prompt,
                "plan": plan,
                "task_plan": task_plan,
                "current_phase": AgentPhase.FAILED,
                "status": "FAILED",
                "errors": ["No coder state or task plan available"],
            }

    files_to_review = set()
    preserved_reviews = {}

    if existing_review_state is None:
        review_state = ReviewState(reviews=[], iteration=0, max_iterations=5)
        files_to_review = {
            step.filepath for step in coder_state.task_plan.implementation_steps
        }
        print(f"First review iteration - reviewing all {len(files_to_review)} files")
    else:
        review_state = ReviewState(
            reviews=[],
            iteration=existing_review_state.iteration + 1,
            max_iterations=existing_review_state.max_iterations,
        )
        for review in existing_review_state.reviews:
            if review.passed:
                preserved_reviews[review.filepath] = review
            else:
                files_to_review.add(review.filepath)
        print(f"Re-review iteration - {len(files_to_review)} failed files to re-review")
        print(f"Preserving {len(preserved_reviews)} already-passed files")

    print(f"\n{'='*50}")
    print(
        f"CODE REVIEW - Iteration {review_state.iteration + 1}/{review_state.max_iterations}"
    )
    print(f"{'='*50}\n")

    if review_state.iteration >= review_state.max_iterations:
        print("Max review iterations reached, proceeding anyway")
        review_state.reviews = list(preserved_reviews.values())
        review_state.all_passed = True
        return {
            "user_prompt": user_prompt,
            "plan": plan,
            "task_plan": task_plan,
            "coder_state": coder_state,
            "review_state": review_state,
            "current_phase": AgentPhase.REVIEWING,
            "status": "review_max_iterations",
        }

    llm = get_llm("review")
    steps = coder_state.task_plan.implementation_steps
    all_passed = True

    for step in steps:
        filepath = step.filepath

        if filepath in preserved_reviews:
            review_state.reviews.append(preserved_reviews[filepath])
            print(f"PRESERVED {filepath}: Already passed (skipping re-review)")
            continue

        if filepath not in files_to_review:
            print(f"SKIP {filepath}: Not in review queue")
            continue

        content = read_file.invoke({"path": filepath})

        if not content or content.startswith("ERROR") or len(content.strip()) < 5:
            review = CodeReview(
                filepath=filepath,
                issues=[
                    CodeIssue(
                        issue_type="missing",
                        description="File does not exist or is empty",
                        suggestion="Ensure the file is created with proper content",
                        severity=ReviewSeverity.CRITICAL,
                    )
                ],
                passed=False,
                overall_quality=0,
                summary="File missing or empty",
            )
            review_state.reviews.append(review)
            all_passed = False
            print(f"FAIL {filepath}: Missing or empty")
            continue

        try:
            prompt = reviewer_prompt(filepath, content, step.task_description)
            review = None

            try:
                review = llm.with_structured_output(CodeReview).invoke(prompt)
            except Exception as struct_error:
                error_str = str(struct_error)
                if "failed_generation" in error_str:
                    review = parse_review_from_error(error_str, filepath)

            if review is None:
                file_ext = filepath.split(".")[-1].lower() if "." in filepath else ""

                simple_prompt = f"""Review this {file_ext.upper()} code file. Be concise.

                    File: {filepath}

                    Code:
                    {content[:]}

                    First line: Write only PASS or FAIL
                    Second line: If FAIL, write ONE specific issue (no markdown, no tables, plain text only)

                    Example good response:
                    FAIL
                    Missing event listener for button click functionality

                    Example good response:
                    PASS
                    Code looks good
                    """
                simple_response = llm.invoke(simple_prompt)
                response_text = simple_response.content.strip()
                lines = response_text.split("\n")
                first_line = lines[0].strip().upper() if lines else ""

                is_pass = first_line == "PASS" or (
                    first_line.startswith("PASS") and "FAIL" not in first_line
                )

                issues = []
                if not is_pass:
                    extracted_issues = extract_issues_from_response(response_text)

                    if extracted_issues:
                        for issue_text in extracted_issues[:2]:
                            issues.append(
                                CodeIssue(
                                    issue_type="quality",
                                    description=issue_text[:200],
                                    suggestion="Fix the identified issue",
                                    severity=ReviewSeverity.MEDIUM,
                                )
                            )
                    else:
                        second_line = lines[1].strip() if len(lines) > 1 else ""
                        second_line = clean_review_response(second_line)

                        if (
                            second_line
                            and len(second_line) > 10
                            and len(second_line) < 200
                        ):
                            issue_desc = second_line
                        else:
                            issue_desc = f"Code review failed for {filepath}"

                        issues.append(
                            CodeIssue(
                                issue_type="quality",
                                description=issue_desc,
                                suggestion="Review and fix the code",
                                severity=ReviewSeverity.MEDIUM,
                            )
                        )

                review = CodeReview(
                    filepath=filepath,
                    issues=issues,
                    passed=is_pass,
                    overall_quality=7 if is_pass else 5,
                    summary=f"{'PASS' if is_pass else 'FAIL'}",
                )

            if not review.passed and len(review.issues) == 0:
                review.issues.append(
                    CodeIssue(
                        issue_type="unspecified",
                        description=f"Review failed for {filepath} without specific issues",
                        suggestion="Manual review recommended",
                        severity=ReviewSeverity.MEDIUM,
                    )
                )

            review_state.reviews.append(review)

            if review.passed:
                print(f"PASS {filepath}: Quality {review.overall_quality}/10")
            else:
                print(f"FAIL {filepath}: {len(review.issues)} issue(s)")
                for issue in review.issues[:2]:
                    print(
                        f"     - [{issue.severity.value}] {issue.description[:60]}..."
                    )
                all_passed = False

        except Exception as e:
            print(f"Review error for {filepath}: {str(e)}")
            review = CodeReview(
                filepath=filepath,
                issues=[],
                passed=True,
                overall_quality=6,
                summary=f"Review error: {str(e)[:50]}",
            )
            review_state.reviews.append(review)

    review_state.all_passed = all_passed
    passed_count = sum(1 for r in review_state.reviews if r.passed)
    failed_count = sum(1 for r in review_state.reviews if not r.passed)

    print(f"\n{'='*50}")
    print(f"REVIEW SUMMARY: {passed_count} passed, {failed_count} failed")
    if all_passed:
        print("ALL FILES PASSED REVIEW")
    else:
        print("Some files need fixes")
        for r in review_state.reviews:
            if not r.passed:
                print(f"  - {r.filepath}: {len(r.issues)} issue(s)")
    print(f"{'='*50}\n")

    return {
        "user_prompt": user_prompt,
        "plan": plan,
        "task_plan": task_plan,
        "coder_state": coder_state,
        "review_state": review_state,
        "current_phase": AgentPhase.REVIEWING,
        "status": "reviewed",
    }
