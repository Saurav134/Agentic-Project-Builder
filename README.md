# 🚀 Agentic Project Builder

A multi-agent AI system that automatically generates complete software
projects from a single natural language prompt.

Built with LangGraph, LangChain, and FastAPI, this system orchestrates
specialized AI agents to design, implement, review, test, and finalize a
project end-to-end.

------------------------------------------------------------------------

## 🧠 Agent Architecture

The system operates as a **state-driven multi-agent workflow**
orchestrated by LangGraph.

Each agent performs a specialized role and passes structured state to
the next stage, forming a self-correcting software generation loop.

------------------------------------------------------------------------

## 🔁 Workflow Overview

    User Prompt
        ↓
    Planner
        ↓
    Architect
        ↓
    Coder ────────┐
        ↑          │ (loops until all files created)
        └──────────┘
        ↓
    Reviewer ──────┐
        ↑          │ (fix loop if issues found)
        └─ Fixer ──┘
        ↓
    Test Generator
        ↓
    Test Runner
        ↓
    Finalizer
        ↓
    END

This design creates two convergence loops:

-   **Implementation Loop** -- ensures all files are generated\
-   **Quality Loop** -- ensures generated code meets review standards

------------------------------------------------------------------------

## 🤖 Agent Responsibilities

### 🧩 Planner Agent

Transforms the user prompt into a structured project plan including: -
project name - tech stack - features - files to create

This acts as the blueprint for the system.

------------------------------------------------------------------------

### 🏗 Architect Agent

Expands the plan into detailed implementation tasks.

Produces: - ordered implementation steps - file dependencies - expected
exports

This converts *what to build* into *how to build it*.

------------------------------------------------------------------------

### 💻 Coder Agent

Implements files one-by-one using the task plan.

Capabilities: - reads existing project context - writes files using
tools - ensures naming consistency

This is the execution engine of the system.

------------------------------------------------------------------------

### 🔍 Reviewer Agent

Performs automated code review.

Checks: - correctness - completeness - consistency - best practices

If issues exist, the system enters the repair loop.

------------------------------------------------------------------------

### 🛠 Fixer Agent

Automatically repairs issues flagged by the reviewer.

Updates only problematic files while preserving correct ones.

This creates a **self-healing generation cycle**.

------------------------------------------------------------------------

### 🧪 Test Generator Agent

Creates tests based on project type:

-   Web apps → manual checklist
-   Python apps → pytest suite

Ensures the project is verifiable.

------------------------------------------------------------------------

### ▶️ Test Runner Agent

Executes tests or provides testing instructions.

Produces: - pass/fail results - outputs/logs

------------------------------------------------------------------------

### 📦 Finalizer Agent

Completes the project by generating:

-   README
-   final summary
-   output location

------------------------------------------------------------------------

## ▶️ Running the Project

### CLI Mode

``` bash
python main.py
```

Enter your project idea interactively.

------------------------------------------------------------------------

### API Mode

``` bash
uvicorn api:app --reload
```

Generate project:

    POST /api/generate
    {
      "prompt": "Create a Python CLI calculator"
    }

------------------------------------------------------------------------

### Web UI

Open:

    http://localhost:8000

Enter your prompt and watch the pipeline execute in real time.

------------------------------------------------------------------------

## 📦 Output

Generated projects are saved in:

    generated_project/

This location is configurable via:

    PROJECT_OUTPUT_DIR

------------------------------------------------------------------------

## 🧩 Tech Stack

-   LangGraph -- orchestration
-   LangChain -- tools & prompts
-   Groq LLMs -- reasoning & coding
-   FastAPI -- API + streaming UI
-   Pydantic -- structured state
-   Rich -- CLI experience

------------------------------------------------------------------------

## 👨‍💻 Author

**Saurav Deshpande**

------------------------------------------------------------------------