import json
import re
import math
from dataclasses import dataclass, field
from typing import Optional

from pyron.agent.reflection import is_task_complex


@dataclass
class Step:
    id: int
    description: str
    status: str = "pending"
    result: Optional[str] = None


@dataclass
class Plan:
    goal: str
    steps: list[Step] = field(default_factory=list)
    current_step: int = 0
    complexity: str = "simple"

    def to_json(self) -> str:
        return json.dumps({
            "goal": self.goal,
            "complexity": self.complexity,
            "steps": [
                {"id": s.id, "description": s.description, "status": s.status, "result": s.result}
                for s in self.steps
            ],
            "current_step": self.current_step,
        }, indent=2)

    def summary(self) -> str:
        lines = [f"Goal: {self.goal}", f"Complexity: {self.complexity}", ""]
        for s in self.steps:
            marker = ">" if s.id == self.current_step else " "
            lines.append(f"  {marker} [{s.status:9}] Step {s.id}: {s.description}")
        return "\n".join(lines)


def assess_complexity(goal: str) -> str:
    goal_lower = goal.lower()
    complexity_score = 0

    keywords_light = {"list", "show", "print", "echo", "find", "search", "count", "check"}
    keywords_medium = {"create", "write", "read", "copy", "move", "delete", "rename",
                       "install", "download", "build", "compile", "run"}
    keywords_complex = {"refactor", "debug", "test", "analyze", "design", "architect",
                        "optimize", "migrate", "integrate", "deploy", "configure",
                        "implement", "develop", "fix", "resolve"}

    for kw in keywords_light:
        if kw in goal_lower:
            complexity_score += 1
    for kw in keywords_medium:
        if kw in goal_lower:
            complexity_score += 3
    for kw in keywords_complex:
        if kw in goal_lower:
            complexity_score += 5

    if len(goal) > 200:
        complexity_score += 2
    if len(goal) > 500:
        complexity_score += 3

    if complexity_score <= 3:
        return "simple"
    elif complexity_score <= 8:
        return "medium"
    else:
        return "complex"


def compute_max_steps(complexity: str) -> int:
    if complexity == "simple":
        return 3
    elif complexity == "medium":
        return 6
    else:
        return 12


def get_plan_depth_instruction(complexity: str) -> str:
    if complexity == "simple":
        return "Create a minimal plan (1-3 steps). Be concise."
    elif complexity == "medium":
        return "Create a focused plan (3-6 steps). Cover the main actions needed."
    else:
        return "Create a detailed plan (up to 12 steps). Break down all sub-tasks."


SYSTEM_PLAN_PROMPT = """You are a planning agent. Given a user goal, create a step-by-step plan.
Output each step on a new line, numbered like:
1. First step description
2. Second step description
...

Only output the numbered steps, nothing else. Keep steps concrete and actionable."""


def extract_plan(text: str, goal: str) -> Optional[Plan]:
    lines = text.strip().split("\n")
    steps = []
    step_id = 0

    for line in lines:
        m = re.match(r"^\d+[.)]\s+(.+)", line.strip())
        if m:
            step_id += 1
            steps.append(Step(id=step_id, description=m.group(1).strip()))

    if not steps:
        return None

    complexity = assess_complexity(goal)
    max_steps = compute_max_steps(complexity)

    if len(steps) > max_steps:
        steps = steps[:max_steps]

    plan = Plan(goal=goal, steps=steps, current_step=1, complexity=complexity)

    if complexity == "simple" and len(steps) >= 1:
        pass
    elif complexity == "simple" and len(steps) == 0:
        steps.append(Step(id=1, description="Execute the requested operation"))
        plan.steps = steps

    return plan


SYSTEM_EXECUTE_PROMPT = """You are Pyron, an autonomous AI agent.
You have access to tools that let you execute bash commands, read/write files, and explore directories.

Available tools:
{tools}

For each step, respond with a JSON object:
{{
  "thought": "your reasoning about what to do next",
  "tool": "tool_name",
  "parameters": {{ "param1": "value1", ... }}
}}

When the task is complete, respond with:
{{
  "thought": "summary of what was accomplished",
  "complete": true,
  "result": "final result message"
}}

Always think step by step. Use tools to gather information before taking actions.
"""
