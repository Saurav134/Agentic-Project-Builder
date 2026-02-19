"""
LLM Configuration Module
Handles LLM provider selection and initialization.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_groq import ChatGroq


project_root = Path(__file__).parent.parent
env_path = project_root / ".env"

load_dotenv(env_path, override=True)


api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise ValueError(
        "GROQ_API_KEY not found! Please ensure:\n"
        "1. .env file exists in project root\n"
        "2. It contains: GROQ_API_KEY=your_key_here\n"
        "3. No quotes or spaces around the value"
    )


class LLMProvider:
    """Manages LLM instances for different tasks."""

    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER", "groq")
        self.api_key = os.getenv("GROQ_API_KEY")
        self._instances = {}
        self._initialize_llms()

    def _initialize_llms(self):
        """Initialize LLM instances based on provider."""

        if self.provider == "groq":

            self._instances = {
                "planning": ChatGroq(
                    model="moonshotai/kimi-k2-instruct",
                    temperature=0.7,
                    max_tokens=4096,
                    api_key=self.api_key,
                ),
                "architect": ChatGroq(
                    model="llama-3.3-70b-versatile",
                    temperature=0.2,
                    max_tokens=8192,
                    api_key=self.api_key,
                ),
                "coding": ChatGroq(
                    model="moonshotai/kimi-k2-instruct",
                    temperature=0.1,
                    max_tokens=4096,
                    api_key=self.api_key,
                ),
                "review": ChatGroq(
                    model="openai/gpt-oss-120b",
                    temperature=0.2,
                    max_tokens=8192,
                    api_key=self.api_key,
                ),
                "fixer": ChatGroq(
                    model="llama-3.3-70b-versatile",
                    temperature=0.1,
                    max_tokens=4096,
                    api_key=self.api_key,
                ),
                "default": ChatGroq(
                    model="llama-3.3-70b-versatile",
                    temperature=0.3,
                    max_tokens=4096,
                    api_key=self.api_key,
                ),
            }
        else:

            default_llm = ChatGroq(
                model="llama-3.3-70b-versatile",
                temperature=0.3,
                api_key=self.api_key,
            )
            self._instances = {
                "planning": default_llm,
                "coding": default_llm,
                "review": default_llm,
                "default": default_llm,
            }

    def get(self, task_type: str = "default"):
        """Get LLM instance for a specific task type."""
        return self._instances.get(task_type, self._instances["default"])

    def get_planning_llm(self):
        return self.get("planning")

    def get_coding_llm(self):
        return self.get("coding")

    def get_review_llm(self):
        return self.get("review")


llm_provider = LLMProvider()


def get_llm(task_type: str = "default"):
    """Get an LLM instance for the specified task type."""
    return llm_provider.get(task_type)
