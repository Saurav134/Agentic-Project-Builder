#!/usr/bin/env python3
"""
Agentic Project Builder - CLI Entry Point
A multi-agent system for automated software project generation.
"""

import argparse
import sys
import os
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

# Load environment variables
load_dotenv(override=True)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from agent.graph import agent, print_graph_structure
from agent.tools import init_project_root, get_project_root


console = Console()


def display_banner():
    """Display the application banner."""
    banner = """
     ===============================================================
    |                                                               |
    |               AGENTIC PROJECT BUILDER                         |
    |                                                               |
    |     Multi-Agent System for Automated Code Generation          |
    |              Built by Saurav Deshpande                        |
    |                                                               |
     ===============================================================
    """
    console.print(banner, style="bold cyan")


def display_agents():
    """Display information about the agents."""
    agents_info = """
    [bold]Agents in Pipeline:[/bold]
    
    1.  [cyan]Planner[/cyan]      - Converts your idea into a project plan
    2.   [cyan]Architect[/cyan]   - Breaks down plan into implementation tasks
    3.  [cyan]Coder[/cyan]        - Writes the actual code files
    4.  [cyan]Reviewer[/cyan]     - Reviews code for quality and issues
    5.  [cyan]Fixer[/cyan]        - Fixes issues found in review
    6.  [cyan]Test Gen[/cyan]     - Generates test cases
    7.  [cyan]Test Runner[/cyan]  - Runs the tests
    8.  [cyan]Finalizer[/cyan]    - Creates documentation
    """
    console.print(Panel(agents_info, title="Agent Pipeline", border_style="blue"))


def run_interactive():
    """Run in interactive mode."""
    display_banner()
    display_agents()

    console.print("\n[bold green]Enter your project idea below:[/bold green]")
    console.print("[dim]Examples:[/dim]")
    console.print(
        "[dim]  • Build a colorful todo app with HTML, CSS, and JavaScript[/dim]"
    )
    console.print("[dim]  • Create a Python CLI calculator with basic operations[/dim]")
    console.print("[dim]  • Build a React counter app with increment/decrement[/dim]")
    console.print()

    try:
        user_prompt = console.input("[bold cyan]Your idea:[/bold cyan] ")

        if not user_prompt.strip():
            console.print("[red]Error: Please provide a project description[/red]")
            return 1

        return run_generation(user_prompt.strip())

    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user.[/yellow]")
        return 0


def run_generation(user_prompt: str, recursion_limit: int = 100) -> int:
    """
    Run the project generation pipeline.

    Args:
        user_prompt: The project description
        recursion_limit: Maximum recursion depth

    Returns:
        Exit code (0 for success)
    """
    # Initialize project directory
    project_root = init_project_root()

    console.print(f"\n[bold]Project will be generated in:[/bold] {project_root}")
    console.print(f"[bold] Prompt:[/bold] {user_prompt}\n")

    start_time = datetime.now()

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Generating project...", total=None)

            # Run the agent
            result = agent.invoke(
                {"user_prompt": user_prompt}, {"recursion_limit": recursion_limit}
            )

            progress.update(task, completed=True)

        # Display results
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        if result.get("status") == "DONE":
            console.print(
                f"\n[bold green] Project generated successfully![/bold green]"
            )
            console.print(f"[dim]Time taken: {duration:.1f} seconds[/dim]")

            if result.get("final_summary"):
                console.print(result["final_summary"])

            return 0
        else:
            console.print(
                f"\n[bold yellow] Project generation completed with status: {result.get('status')}[/bold yellow]"
            )

            if result.get("errors"):
                console.print("[red]Errors:[/red]")
                for error in result["errors"]:
                    console.print(f"  • {error}")

            return 1

    except Exception as e:
        console.print(f"\n[bold red] Error during generation:[/bold red]")
        console.print(f"[red]{str(e)}[/red]")

        import traceback

        if os.getenv("DEBUG_MODE", "false").lower() == "true":
            traceback.print_exc()

        return 1


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Agentic Project Builder - Generate software projects using AI agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py
  python main.py --prompt "Build a todo app with React"
  python main.py --prompt "Create a Python calculator" --recursion-limit 150
  python main.py --show-graph
  python main.py --stats
        """,
    )

    parser.add_argument(
        "--prompt",
        "-p",
        type=str,
        help="Project description (if not provided, runs in interactive mode)",
    )

    parser.add_argument(
        "--recursion-limit",
        "-r",
        type=int,
        default=100,
        help="Recursion limit for agent processing (default: 100)",
    )

    parser.add_argument(
        "--show-graph",
        "-g",
        action="store_true",
        help="Display the agent graph structure and exit",
    )

    parser.add_argument(
        "--stats",
        "-s",
        action="store_true",
        help="Show project memory statistics and exit",
    )

    parser.add_argument(
        "--version", "-v", action="version", version="Agentic Project Builder v2.0.0"
    )

    args = parser.parse_args()

    # Handle special commands
    if args.show_graph:
        print_graph_structure()
        return 0

    # Check for API key
    if not os.getenv("GROQ_API_KEY"):
        console.print(
            "[bold red]Error: GROQ_API_KEY not found in environment[/bold red]"
        )
        console.print("\nTo get a FREE API key:")
        console.print("1. Go to https://console.groq.com")
        console.print("2. Sign up for free")
        console.print("3. Create an API key")
        console.print("4. Add to .env file: GROQ_API_KEY=your_key_here")
        return 1

    # Run generation
    if args.prompt:
        return run_generation(args.prompt, args.recursion_limit)
    else:
        return run_interactive()


if __name__ == "__main__":
    sys.exit(main())
