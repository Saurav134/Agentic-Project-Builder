"""
LangGraph Workflow Definition
Defines the multi-agent graph for project generation.
"""

import os
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END

load_dotenv(override=True)
from langsmith import Client

Client()

from builder.states import AgentPhase
from builder.tools import init_project_root
from builder.agents import (
    planner_agent,
    architect_agent,
    coder_agent,
    reviewer_agent,
    fixer_agent,
    test_generator_agent,
    test_runner_agent,
    finalizer_agent,
)

init_project_root()


def route_after_coder(state: dict) -> str:
    """Determine next step after coding."""
    coder_state = state.get("coder_state")

    if coder_state is None:
        return "reviewer"

    total_steps = len(coder_state.task_plan.implementation_steps)
    current_idx = coder_state.current_step_idx

    if current_idx >= total_steps:
        return "reviewer"
    else:
        return "coder"


def route_after_review(state: dict) -> str:
    """Determine next step after review."""
    review_state = state.get("review_state")

    if review_state is None:
        return "test_generator"

    if review_state.all_passed:
        return "test_generator"
    elif review_state.iteration >= review_state.max_iterations:
        return "test_generator"
    else:
        return "fixer"


def route_after_tests(state: dict) -> str:
    """Determine next step after tests."""
    return "finalizer"


def create_graph():
    """Create the LangGraph workflow."""

    graph = StateGraph(dict)

    graph.add_node("planner", planner_agent)
    graph.add_node("architect", architect_agent)
    graph.add_node("coder", coder_agent)
    graph.add_node("reviewer", reviewer_agent)
    graph.add_node("fixer", fixer_agent)
    graph.add_node("test_generator", test_generator_agent)
    graph.add_node("test_runner", test_runner_agent)
    graph.add_node("finalizer", finalizer_agent)

    graph.set_entry_point("planner")

    graph.add_edge("planner", "architect")
    graph.add_edge("architect", "coder")

    graph.add_conditional_edges(
        "coder", route_after_coder, {"coder": "coder", "reviewer": "reviewer"}
    )

    graph.add_conditional_edges(
        "reviewer",
        route_after_review,
        {"fixer": "fixer", "test_generator": "test_generator"},
    )

    graph.add_edge("fixer", "reviewer")
    graph.add_edge("test_generator", "test_runner")

    graph.add_conditional_edges(
        "test_runner", route_after_tests, {"finalizer": "finalizer"}
    )

    graph.add_edge("finalizer", END)

    return graph


def create_agent():
    """Create and compile the agent graph."""
    graph = create_graph()

    return graph.compile()


agent = create_agent()


def print_graph_structure():
    """Print the graph structure for debugging."""
    print(
        """
    AGENTIC PROJECT BUILDER - WORKFLOW
    
    PLANNER -> ARCHITECT -> CODER (loop) -> REVIEWER <---------------
                                               |                     | 
                              [PASS] ----------+---------- [FAIL]    |
                                |                            |       |
                                v                            v       |         
                         TEST_GENERATOR                   FIXER ------
                                |                            
                                v                            
                          TEST_RUNNER  
                                |
                                v
                           FINALIZER
                                |
                                v
                              [END]
    """
    )


if __name__ == "__main__":
    print_graph_structure()
