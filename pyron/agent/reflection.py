import time
import json
from dataclasses import dataclass, field
from typing import Optional

from pyron.api.client import Message


@dataclass
class ReflectionResult:
    analysis: str
    root_cause: str
    suggestions: list[str]
    should_retry: bool
    retry_strategy: Optional[str] = None


def is_task_complex(goal: str, steps: list) -> bool:
    if len(steps) > 5:
        return True
    keywords = ["refactor", "architect", "design", "debug", "analyze",
                 "complex", "large", "multiple", "integration", "test"]
    goal_lower = goal.lower()
    count = sum(1 for kw in keywords if kw in goal_lower)
    if count >= 2:
        return True
    if len(goal) > 300:
        return True
    return False


def should_reflect(step_id: int, attempt: int, total_steps: int, goal: str) -> bool:
    if attempt > 2:
        return True
    if is_task_complex(goal, list(range(total_steps))):
        return step_id % 3 == 0
    return False


def perform_reflection(goal: str, step_history: list[dict], failed_result: str) -> ReflectionResult:
    analysis_parts = []
    root_cause = ""
    suggestions = []
    retry_needed = False
    retry_strategy = None

    if "timeout" in failed_result.lower() or "timed out" in failed_result.lower():
        root_cause = "Command timed out - needs optimization or longer timeout"
        suggestions = [
            "Break the command into smaller parts",
            "Increase timeout if operation is inherently slow",
            "Check if there's an infinite loop",
        ]
        retry_needed = True
        retry_strategy = "Split into smaller operations with individual timeouts"

    elif "exit code" in failed_result.lower():
        root_cause = f"Command failed: {failed_result}"
        suggestions = [
            "Check command syntax for errors",
            "Verify required files or directories exist",
            "Ensure proper permissions",
        ]
        retry_needed = True
        retry_strategy = "Verify prerequisites before retrying"

    elif "not found" in failed_result.lower():
        root_cause = "Referenced resource does not exist"
        suggestions = [
            "Create the required file or directory first",
            "Check the path for typos",
            "Use glob or list_directory to discover available resources",
        ]
        retry_needed = True
        retry_strategy = "Create prerequisites before retrying"

    elif "permission" in failed_result.lower():
        root_cause = "Permission denied"
        suggestions = [
            "Use appropriate permissions",
            "Check file ownership",
            "Use sudo if applicable",
        ]
        retry_needed = True
        retry_strategy = "Fix permissions or use authorized location"

    else:
        root_cause = f"Unexpected error: {failed_result}"
        suggestions = [
            "Try an alternative approach",
            "Verify inputs are valid",
            "Check system state",
        ]
        retry_needed = True
        retry_strategy = "Try alternative approach"

    analysis = (
        f"Reflection on step failure:\n"
        f"  Root cause: {root_cause}\n"
        f"  Suggestions:\n"
    )
    for s in suggestions:
        analysis += f"    - {s}\n"
    if retry_strategy:
        analysis += f"  Retry strategy: {retry_strategy}\n"

    return ReflectionResult(
        analysis=analysis,
        root_cause=root_cause,
        suggestions=suggestions,
        should_retry=retry_needed,
        retry_strategy=retry_strategy,
    )
