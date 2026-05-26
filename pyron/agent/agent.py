import json
import re
from typing import Optional

from pyron.api.client import ApiClient, Message
from pyron.agent.tools import AVAILABLE_TOOLS, execute_tool
from pyron.agent.planning import (
    Plan,
    Step,
    extract_plan,
    SYSTEM_PLAN_PROMPT,
    SYSTEM_EXECUTE_PROMPT,
)


class Agent:
    def __init__(self):
        self.client = ApiClient()
        self.plan: Optional[Plan] = None
        self.history: list[Message] = []

    def run(self, goal: str) -> str:
        plan = self._create_plan(goal)
        if not plan:
            return "Failed to create a plan for this goal."

        self.plan = plan
        tools_desc = "\n".join(
            f"  {name}: {info['description']}"
            for name, info in AVAILABLE_TOOLS.items()
        )

        context = f"Goal: {goal}\n\nPlan:\n{plan.summary()}\n\nBegin executing step 1."

        self.history = [
            Message("system", SYSTEM_EXECUTE_PROMPT.format(tools=tools_desc)),
            Message("user", context),
        ]

        for step in plan.steps:
            step.status = "in_progress"
            result = self._execute_step(step)
            step.status = "done"
            step.result = result

        return self._summarize()

    def _create_plan(self, goal: str) -> Optional[Plan]:
        messages = [
            Message("system", SYSTEM_PLAN_PROMPT),
            Message("user", f"Create a plan for: {goal}"),
        ]
        response = self.client.complete(messages)
        return extract_plan(response.content, goal)

    def _execute_step(self, step: Step) -> str:
        max_attempts = 5
        for attempt in range(max_attempts):
            messages = self.history + [
                Message(
                    "user",
                    f"Execute step {step.id}: {step.description}\n"
                    f"Previous results: {step.result or 'none'}",
                )
            ]

            response = self.client.complete(messages)
            content = response.content.strip()

            action = self._parse_action(content)
            if action is None:
                self.history.append(Message("assistant", content))
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
                continue

            result = execute_tool(tool_name, params)
            result_text = json.dumps(result.to_dict(), indent=2)

            self.history.append(Message("assistant", content))
            self.history.append(Message("user", f"Result:\n{result_text}"))

        return "Max attempts reached for this step."

    def _parse_action(self, content: str) -> Optional[dict]:
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
        steps_summary = []
        for step in self.plan.steps:
            status = "done" if step.status == "done" else "failed"
            steps_summary.append(f"  Step {step.id}: {step.description} [{status}]")
        return f"Goal: {self.plan.goal}\n" + "\n".join(steps_summary)
