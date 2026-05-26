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

    def to_json(self) -> str:
        return json.dumps({
            "goal": self.goal,
            "steps": [
                {"id": s.id, "description": s.description, "status": s.status, "result": s.result}
                for s in self.steps
            ],
            "current_step": self.current_step,
        }, indent=2)

    def summary(self) -> str:
        lines = [f"Goal: {self.goal}", ""]
        for s in self.steps:
            marker = ">" if s.id == self.current_step else " "
            lines.append(f"  {marker} [{s.status:9}] Step {s.id}: {s.description}")
        return "\n".join(lines)


def extract_plan(text: str, goal: str) -> Optional[Plan]:
    lines = text.strip().split("\n")
    steps = []
    step_id = 0

    for line in lines:
        m = re.match(r"^\d+[.)]\s+(.+)", line.strip())
        if m:
            step_id += 1
            steps.append(Step(id=step_id, description=m.group(1).strip()))

    if steps:
        return Plan(goal=goal, steps=steps, current_step=1)
    return None


SYSTEM_PLAN_PROMPT = """You are a planning agent. Given a user goal, create a step-by-step plan.
Output each step on a new line, numbered like:
1. First step description
2. Second step description
...

Only output the numbered steps, nothing else."""


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

Always think step by step. Use tools to gather information before taking actions."""
