"""
State Models for the Agentic Project Builder
Defines all Pydantic models for state management across agents.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field, ConfigDict


# ============== Enums ==============


class AgentPhase(str, Enum):
    """Tracks the current phase of project generation."""

    INITIALIZING = "initializing"
    PLANNING = "planning"
    ARCHITECTING = "architecting"
    CODING = "coding"
    REVIEWING = "reviewing"
    FIXING = "fixing"
    TESTING = "testing"
    FINALIZING = "finalizing"
    COMPLETE = "complete"
    FAILED = "failed"


class ReviewSeverity(str, Enum):
    """Severity levels for code review issues."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    PASS = "pass"


# ============== Planning Models ==============


class File(BaseModel):
    """Represents a file to be created in the project."""

    path: str = Field(description="The path to the file relative to project root")
    purpose: str = Field(description="The purpose of this file in the project")
    dependencies: list[str] = Field(
        default_factory=list, description="List of other files this file depends on"
    )


class Plan(BaseModel):
    """The high-level project plan created by the Planner agent."""

    name: str = Field(description="The name of the project")
    description: str = Field(description="A brief description of what the project does")
    techstack: str = Field(
        description="The technology stack (e.g., 'python', 'react', 'html/css/js')"
    )
    features: list[str] = Field(description="List of features the project should have")
    files: list[File] = Field(description="List of files to be created")
    architecture_notes: str = Field(
        default="", description="Additional notes about the architecture"
    )


# ============== Architecture Models ==============


class ImplementationTask(BaseModel):
    """A specific implementation task for the Coder agent."""

    filepath: str = Field(description="The path to the file to be created/modified")
    task_description: str = Field(
        description="Detailed description of what to implement in this file"
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description="Files that must be implemented before this task",
    )
    expected_exports: list[str] = Field(
        default_factory=list,
        description="Functions/classes/variables this file should export",
    )
    priority: int = Field(
        default=0, description="Priority order (lower = higher priority)"
    )


class TaskPlan(BaseModel):
    """The detailed implementation plan created by the Architect agent."""

    model_config = ConfigDict(extra="allow")

    plan: Optional[Plan] = Field(
        default=None, description="Reference to the original plan"
    )
    implementation_steps: list[ImplementationTask] = Field(
        description="Ordered list of implementation tasks"
    )
    total_estimated_tokens: int = Field(
        default=0, description="Estimated token usage for implementation"
    )


# ============== Coder State ==============


class CoderState(BaseModel):
    """Tracks the progress of the Coder agent."""

    task_plan: TaskPlan = Field(description="The task plan being implemented")
    current_step_idx: int = Field(default=0, description="Current step index")
    completed_files: list[str] = Field(
        default_factory=list, description="List of successfully created files"
    )
    failed_files: list[str] = Field(
        default_factory=list, description="List of files that failed to create"
    )
    current_file_content: Optional[str] = Field(
        default=None, description="Content of the file currently being worked on"
    )


# ============== Review Models ==============


class CodeIssue(BaseModel):
    """A specific issue found during code review."""

    line_number: Optional[int] = Field(
        default=None, description="Line number if applicable"
    )
    issue_type: str = Field(
        description="Type of issue (e.g., 'syntax', 'logic', 'security')"
    )
    description: str = Field(description="Description of the issue")
    suggestion: str = Field(description="Suggested fix")
    severity: ReviewSeverity = Field(description="Severity of the issue")


class CodeReview(BaseModel):
    """Review results for a single file."""

    filepath: str = Field(description="Path to the reviewed file")
    issues: list[CodeIssue] = Field(
        default_factory=list, description="List of issues found"
    )
    passed: bool = Field(description="Whether the file passed review")
    overall_quality: int = Field(
        default=0, ge=0, le=10, description="Overall quality score (0-10)"
    )
    summary: str = Field(default="", description="Summary of the review")


class ReviewState(BaseModel):
    """Tracks the state of the code review process."""

    reviews: list[CodeReview] = Field(default_factory=list)
    iteration: int = Field(default=0, description="Current review iteration")
    max_iterations: int = Field(default=3, description="Maximum review iterations")
    all_passed: bool = Field(default=False, description="Whether all files passed")


# ============== Testing Models ==============


class TestCase(BaseModel):
    """A test case to be generated."""

    test_name: str = Field(description="Name of the test")
    test_type: str = Field(description="Type: 'unit', 'integration', 'e2e'")
    target_file: str = Field(description="File being tested")
    test_code: str = Field(description="The test code")
    description: str = Field(default="", description="What the test verifies")


class TestPlan(BaseModel):
    """Plan for testing the generated project."""

    test_framework: str = Field(description="Testing framework to use")
    test_files: list[TestCase] = Field(default_factory=list)
    setup_instructions: str = Field(default="", description="How to set up testing")


class TestResult(BaseModel):
    """Results from running tests."""

    test_name: str
    passed: bool
    output: str = Field(default="")
    error: str = Field(default="")
    duration_ms: int = Field(default=0)


class TestRunState(BaseModel):
    """State of test execution."""

    test_plan: Optional[TestPlan] = None
    results: list[TestResult] = Field(default_factory=list)
    all_passed: bool = Field(default=False)
    total_tests: int = Field(default=0)
    passed_tests: int = Field(default=0)


# ============== Execution Logging ==============


class ExecutionLog(BaseModel):
    """A log entry for tracking execution."""

    timestamp: datetime = Field(default_factory=datetime.now)
    phase: AgentPhase
    agent: str = Field(description="Name of the agent")
    message: str
    duration_ms: Optional[int] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


# ============== Main Project State ==============


class ProjectState(BaseModel):
    """
    Central state object for the entire project generation pipeline.
    This is passed between all agents in the graph.
    """

    model_config = ConfigDict(extra="allow")

    # Input
    user_prompt: str = Field(description="Original user request")

    # Planning outputs
    plan: Optional[Plan] = None
    task_plan: Optional[TaskPlan] = None

    # Execution states
    coder_state: Optional[CoderState] = None
    review_state: Optional[ReviewState] = None
    test_run_state: Optional[TestRunState] = None

    # Status tracking
    current_phase: AgentPhase = Field(default=AgentPhase.INITIALIZING)
    status: str = Field(default="initialized")

    # Logging
    execution_logs: list[ExecutionLog] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    # Timestamps
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    # Output
    project_path: str = Field(default="")
    final_summary: str = Field(default="")

    def log(self, phase: AgentPhase, agent: str, message: str, **metadata):
        """Add a log entry."""
        self.execution_logs.append(
            ExecutionLog(phase=phase, agent=agent, message=message, metadata=metadata)
        )

    def add_error(self, error: str):
        """Record an error."""
        self.errors.append(f"[{datetime.now().isoformat()}] {error}")

    def mark_complete(self):
        """Mark the project as complete."""
        self.completed_at = datetime.now()
        self.current_phase = AgentPhase.COMPLETE
        self.status = "DONE"

    def mark_failed(self, reason: str):
        """Mark the project as failed."""
        self.completed_at = datetime.now()
        self.current_phase = AgentPhase.FAILED
        self.status = "FAILED"
        self.add_error(reason)
