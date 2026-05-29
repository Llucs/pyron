import json
import re
from dataclasses import dataclass, field
from typing import Optional


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
            "steps": [{"id": s.id, "description": s.description, "status": s.status, "result": s.result} for s in self.steps],
            "current_step": self.current_step,
        }, indent=2)

    def summary(self) -> str:
        lines = [f"Goal: {self.goal}", f"Complexity: {self.complexity}", ""]
        for s in self.steps:
            lines.append(f"  [{s.status:9}] Step {s.id}: {s.description}")
        return "\n".join(lines)


def assess_complexity(goal: str) -> str:
    goal_lower = goal.lower()
    score = 0
    light = {"list", "show", "print", "echo", "find", "search", "count", "check"}
    medium = {"create", "write", "read", "copy", "move", "delete", "rename", "install", "download", "build", "compile", "run"}
    heavy = {"refactor", "debug", "test", "analyze", "design", "architect", "optimize", "migrate", "integrate", "deploy", "configure", "implement", "develop", "fix", "resolve"}
    for kw in light:
        if kw in goal_lower:
            score += 1
    for kw in medium:
        if kw in goal_lower:
            score += 3
    for kw in heavy:
        if kw in goal_lower:
            score += 5
    if len(goal) > 200:
        score += 2
    if len(goal) > 500:
        score += 3
    if score <= 3:
        return "simple"
    elif score <= 8:
        return "medium"
    return "complex"


def compute_max_steps(complexity: str) -> int:
    return {"simple": 3, "medium": 6, "complex": 12}.get(complexity, 6)


def get_plan_depth_instruction(complexity: str) -> str:
    if complexity == "simple":
        return "Create a minimal plan (1-3 steps). Be concise and direct."
    elif complexity == "medium":
        return "Create a focused plan (3-6 steps). Cover the main actions."
    return "Create a detailed plan (up to 12 steps). Break down all sub-tasks thoroughly."


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
    return Plan(goal=goal, steps=steps, current_step=1, complexity=complexity)


SYSTEM_PLAN_PROMPT = """You are Pyron, an autonomous AI planning agent with hierarchical memory.
Given a user goal, create a detailed step-by-step plan.
Each step should be specific and actionable. Number each step:
1. First step description
2. Second step description
...
Output only the numbered steps, nothing else."""

SYSTEM_EXECUTE_PROMPT = """{memory_context}

You are Pyron, an autonomous AI agent with expanded memory (~1M tokens effective).
You have access to tools that let you execute bash commands, read/write files, explore directories, search code, fetch web pages, and run Python code.

Available tools:
{tools}

Respond with ONLY a JSON object:
{{"tool": "tool_name", "parameters": {{"param1": "value1"}}}}

When the step is complete, respond with:
{{"complete": true, "result": "what was accomplished"}}

Use tools one at a time. Check results before proceeding."""
