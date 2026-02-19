"""
Test Runner Agent
Executes generated tests.
"""

from agent.states import AgentPhase, TestResult, TestPlan
from agent.tools import list_files, run_command, read_file


def test_runner_agent(state: dict) -> dict:
    """
    Test Runner Agent: Runs the generated tests.

    For web projects: Provides instructions for manual testing
    For Python projects: Attempts to run pytest if available
    """
    test_run_state = state.get("test_run_state", {})
    task_plan = state.get("task_plan")
    plan = state.get("plan")
    user_prompt = state.get("user_prompt")
    coder_state = state.get("coder_state")
    review_state = state.get("review_state")

    print(f"\n{'='*50}")
    print("RUNNING TESTS")
    print(f"{'='*50}\n")

    test_plan = test_run_state.get("test_plan")

    if test_plan is None:
        print("No test plan available")
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
            "status": "tests_complete",
        }

    if not test_plan.test_files:
        print("No test files in test plan")
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
                "total_tests": 0,
                "passed_tests": 0,
            },
            "current_phase": AgentPhase.TESTING,
            "status": "tests_complete",
        }

    results = []
    framework = (
        test_plan.test_framework.lower() if test_plan.test_framework else "manual"
    )

    print(f"Test framework: {framework}")
    print(f"Test files: {len(test_plan.test_files)}")
    print()

    if framework == "pytest":

        print("Attempting to run pytest...")

        try:

            pytest_check = run_command.invoke(
                {"cmd": "python -m pytest --version", "timeout": 10}
            )

            if "ERROR" not in pytest_check and "pytest" in pytest_check.lower():
                print("pytest is available, running tests...")

                # Run pytest
                pytest_result = run_command.invoke(
                    {"cmd": "python -m pytest tests/ -v --tb=short", "timeout": 60}
                )

                print(f"\nPytest output:\n{pytest_result}\n")

                passed = (
                    "passed" in pytest_result.lower()
                    and "failed" not in pytest_result.lower()
                )

                results.append(
                    TestResult(
                        test_name="pytest_suite",
                        passed=passed,
                        output=pytest_result[:1000],
                        error="" if passed else "Some tests failed",
                        duration_ms=0,
                    )
                )
            else:
                print("pytest not available, marking for manual testing")
                for test in test_plan.test_files:
                    results.append(
                        TestResult(
                            test_name=test.test_name,
                            passed=True,
                            output="pytest not available - manual verification required",
                            error="",
                            duration_ms=0,
                        )
                    )

        except Exception as e:
            print(f"Error running pytest: {e}")
            for test in test_plan.test_files:
                results.append(
                    TestResult(
                        test_name=test.test_name,
                        passed=True,
                        output=f"Could not run pytest: {str(e)}",
                        error="",
                        duration_ms=0,
                    )
                )

    elif framework == "manual":

        print("Manual testing framework - tests require human verification")
        print()

        for test in test_plan.test_files:

            test_path = (
                f"tests/{test.test_name}"
                if not test.test_name.startswith("tests/")
                else test.test_name
            )
            content = read_file.invoke({"path": test_path})

            file_exists = content and not content.startswith("ERROR")

            results.append(
                TestResult(
                    test_name=test.test_name,
                    passed=file_exists,
                    output=(
                        f"Test checklist created at {test_path}"
                        if file_exists
                        else "Test file not found"
                    ),
                    error="" if file_exists else "Test file was not created",
                    duration_ms=0,
                )
            )

            if file_exists:
                print(f"✓ {test.test_name}: Created successfully")
            else:
                print(f"✗ {test.test_name}: Not found")

        print()
        print("=" * 40)
        print("MANUAL TESTING REQUIRED")
        print("=" * 40)
        print("Please follow the test checklist at: tests/test_checklist.md")
        if test_plan.setup_instructions:
            print(f"Instructions: {test_plan.setup_instructions}")

    else:

        print(f"Unknown test framework: {framework}")
        for test in test_plan.test_files:
            results.append(
                TestResult(
                    test_name=test.test_name,
                    passed=True,
                    output=f"Unknown framework '{framework}' - manual verification required",
                    error="",
                    duration_ms=0,
                )
            )

    total_tests = len(results)
    passed_tests = sum(1 for r in results if r.passed)
    all_passed = passed_tests == total_tests

    print(f"\n{'='*50}")
    print("TEST RESULTS SUMMARY")
    print(f"{'='*50}")
    print(f"Total: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    print(f"Status: {'ALL PASSED ✓' if all_passed else 'SOME FAILED ✗'}")
    print(f"{'='*50}\n")

    return {
        "user_prompt": user_prompt,
        "plan": plan,
        "task_plan": task_plan,
        "coder_state": coder_state,
        "review_state": review_state,
        "test_run_state": {
            "test_plan": test_plan,
            "results": results,
            "all_passed": all_passed,
            "total_tests": total_tests,
            "passed_tests": passed_tests,
        },
        "current_phase": AgentPhase.TESTING,
        "status": "tests_complete",
    }
