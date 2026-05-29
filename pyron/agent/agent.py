import json
import re
import time
from typing import Optional

from pyron.api.client import ApiClient, Message
from pyron.agent.tools import AVAILABLE_TOOLS, execute_tool, is_fast_path
from pyron.agent.planning import (
    Plan,
    Step,
    extract_plan,
    SYSTEM_PLAN_PROMPT,
    SYSTEM_EXECUTE_PROMPT,
    assess_complexity,
    get_plan_depth_instruction,
)
from pyron.agent.memory import get_memory
from pyron.agent.reflection import should_reflect, perform_reflection


class Agent:
    def __init__(self):
        self.client = ApiClient()
        self.plan: Optional[Plan] = None
        self.history: list[Message] = []
        self.memory = get_memory("default")
        self.step_history: list[dict] = []
        self._step_attempts: dict[int, int] = {}

    def run(self, goal: str) -> str:
        complexity = assess_complexity(goal)
        plan = self._create_plan(goal, complexity)
        if not plan:
            return "Failed to create a plan for this goal."

        self.plan = plan
        execution_prompt = SYSTEM_EXECUTE_PROMPT
        context = f"Goal: {goal}\n\nPlan:\n{plan.summary()}\n\nBegin execution."

        self.history = [
            Message("system", execution_prompt),
            Message("user", context),
        ]

        mem_context = self.memory.get_context(goal, max_items=5)
        if mem_context:
            self.history.insert(1, Message("system", mem_context))

        for step in plan.steps:
            step.status = "in_progress"
            self._step_attempts[step.id] = 0
            result = self._execute_step(step, goal)
            step.status = "done"
            step.result = result
            self.memory.add(
                f"Step {step.id}: {step.description} -> {result[:200]}",
                category="step_result",
                importance=1.0,
                tags=[complexity, f"step_{step.id}"],
            )

        goal_tags = [complexity] + [s.description.split()[0].lower() for s in plan.steps if s.description]
        self.memory.add(
            f"Completed goal: {goal}",
            category="goal",
            importance=2.0,
            tags=goal_tags,
        )

        return self._summarize()

    def _create_plan(self, goal: str, complexity: str) -> Optional[Plan]:
        depth_instruction = get_plan_depth_instruction(complexity)
        messages = [
            Message("system", SYSTEM_PLAN_PROMPT),
            Message("user", f"{depth_instruction}\n\nGoal: {goal}"),
        ]
        response = self.client.complete(messages)
        return extract_plan(response.content, goal)

    def _execute_step(self, step: Step, goal: str) -> str:
        max_attempts = 5
        last_error = ""

        for attempt in range(max_attempts):
            self._step_attempts[step.id] = attempt + 1

            context_msg = (
                f"Execute step {step.id}: {step.description}\n"
                f"Previous result: {step.result or 'none'}\n"
            )
            if last_error and attempt > 0:
                context_msg += f"Previous error: {last_error}\n"

            messages = self.history + [Message("user", context_msg)]
            response = self.client.complete(messages)
            content = response.content.strip()

            action = self._parse_action(content)
            if action is None:
                self.history.append(Message("assistant", content))
                last_error = "No valid action found in response"
                continue

            if action.get("complete"):
                self.history.append(Message("assistant", content))
                return action.get("result", "Task completed")

            tool_name = action.get("tool", "")
            params = action.get("parameters", {})

            if tool_name not in AVAILABLE_TOOLS:
                error_msg = f"Unknown tool: {tool_name}. Available: {', '.join(AVAILABLE_TOOLS.keys())}"
                self.history.append(Message("assistant", content))
                self.history.append(Message("user", error_msg))
                last_error = error_msg
                continue

            result = execute_tool(tool_name, params)
            result_text = json.dumps(result.to_dict(), indent=2)

            self.history.append(Message("assistant", content))

            if result.success and not result.is_real_failure:
                self.history.append(Message("user", f"Result:\n{result_text}"))
                return result.output[:1000]

            self.history.append(Message("user", f"Result (failure):\n{result_text}"))
            last_error = result.error or result.output[:200]

            if should_reflect(step.id, attempt, len(self.plan.steps or []), goal):
                reflection = perform_reflection(goal, self.step_history, last_error)
                self.history.append(Message("system", f"[Reflection]\n{reflection.analysis}"))
                if reflection.retry_strategy:
                    self.history.append(Message("system", f"Retry strategy: {reflection.retry_strategy}"))

        return f"Max attempts ({max_attempts}) reached. Last error: {last_error[:500]}"

    def _parse_action(self, content: str) -> Optional[dict]:
        json_match = re.search(r"\{[^{}]*\}", content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        json_match = re.search(r"\{.*\}", content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        return None

    def _summarize(self) -> str:
        if not self.plan:
            return "No plan executed."
        lines = [f"Goal: {self.plan.goal}", f"Complexity: {self.plan.complexity}", ""]
        for i, step in enumerate(self.plan.steps):
            status = "done" if step.status == "done" else "failed"
            attempts = self._step_attempts.get(step.id, 0)
            lines.append(f"  Step {step.id}: {step.description} [{status}] ({attempts} attempt(s))")
            if step.result:
                lines.append(f"    Result: {step.result[:200]}")
        return "\n".join(lines)
