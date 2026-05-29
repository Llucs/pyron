import json
import os
from typing import Optional, Callable

from pyron.api.client import ApiClient, Message
from pyron.agent.tools import AVAILABLE_TOOLS, execute_tool, _INITIAL_CWD
from pyron.agent.planning import Plan, Step, extract_plan, SYSTEM_PLAN_PROMPT, SYSTEM_EXECUTE_PROMPT
from pyron.memory_manager import MemoryManager, SYSTEM_MASTER_PROMPT
from pyron.config import get_api_config


class Agent:
    def __init__(self, log_fn: Optional[Callable[[str], None]] = None,
                 status_fn: Optional[Callable[[str], None]] = None):
        self.client = ApiClient()
        self.memory = MemoryManager()
        self.plan: Optional[Plan] = None
        self.history: list[Message] = []
        self.goal = ""
        self._log = log_fn or (lambda x: None)
        self._status_fn = status_fn or (lambda x: None)
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self._current_step = 0
        self._total_steps = 0
        self._model = get_api_config().get("model", "unknown")
        self._cwd = _INITIAL_CWD

    def _emit(self, msg: str):
        self._log(msg)

    def _status_line(self) -> str:
        if not self.plan:
            return ""
        total = max(self._total_steps, 1)
        pct = int(self._current_step / total * 100)
        cwd = self._cwd
        home = os.path.expanduser("~")
        if cwd.startswith(home):
            cwd = "~" + cwd[len(home):]
        pt = self.prompt_tokens
        ct = self.completion_tokens
        pt_s = f"{pt/1000:.1f}K" if pt >= 1000 else str(pt)
        ct_s = f"{ct/1000:.1f}K" if ct >= 1000 else str(ct)
        model_s = self._model.split("/")[-1][:20]
        return (
            f"\r\033[K"
            f"\033[36mpyron@{cwd}\033[0m "
            f"\033[2m[\033[0m{model_s}\033[2m]\033[0m "
            f"step {self._current_step}/{self._total_steps} "
            f"({pct}%)"
            f"\033[2m  \u2191{pt_s} \u2193{ct_s}\033[0m"
        )

    def _update_status(self):
        self._status_fn(self._status_line())

    def run(self, goal: str) -> str:
        self.goal = goal
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self._current_step = 0
        self.memory.save_interaction("user", goal, importance=0.9, tags=["goal"])
        self.memory.add_entity("Pyron", "agent", {"type": "autonomous AI"})

        self._emit(f"\033[1mGoal:\033[0m {goal}")
        plan = self._create_plan(goal)
        if not plan:
            return "Failed to create plan."

        self.plan = plan
        self._total_steps = len(plan.steps)
        self._emit(f"\033[1mPlan:\033[0m {len(plan.steps)} steps")
        for s in plan.steps:
            self._emit(f"  \033[2m{s.id}.\033[0m {s.description}")
        self._update_status()

        tools_desc = self._format_tools()
        memory_context = self.memory.retrieve_context(goal)
        system_prompt = SYSTEM_EXECUTE_PROMPT.format(
            memory_context=memory_context,
            tools=tools_desc,
        )
        context = f"Goal: {goal}\n\nPlan:\n{plan.summary()}\n\nBegin executing step 1."

        self.history = [
            Message("system", system_prompt),
            Message("user", context),
        ]
        self.memory.save_interaction("system", SYSTEM_MASTER_PROMPT,
                                     importance=0.8, tags=["system"])
        self.memory.save_interaction("assistant", f"Plan created with {len(plan.steps)} steps",
                                     importance=0.6, tags=["plan"])

        for step in plan.steps:
            step.status = "in_progress"
            self._current_step = step.id
            self._emit(f"\n\033[34m--- Step {step.id}: {step.description} ---\033[0m")

            context_msg = (
                f"Execute step {step.id}: {step.description}\n"
                f"Previous results: {step.result or 'none'}"
            )
            self.memory.save_interaction("user", context_msg, importance=0.7, tags=["step"])
            result = self._execute_step(step)
            step.status = "done"
            step.result = result

            self._emit(f"\033[32m--- Step {step.id}: done ---\033[0m")
            self._update_status()

            self.memory.save_interaction("assistant", f"Step {step.id} completed: {result[:200]}",
                                         importance=0.6, tags=["step_result"])
            self.memory.check_and_compress()
            reflection = self.memory.reflection.reflect(self.memory.knowledge_graph)
            if reflection:
                self._emit(f"\033[33m[Reflection] {reflection}\033[0m")
                self.memory.save_interaction("system", f"[Reflection] {reflection}",
                                             importance=0.5, tags=["reflection"])

        self.memory.apply_forgetting(threshold=0.05)
        return self._summarize()

    def _format_tools(self) -> str:
        lines = []
        for name, info in AVAILABLE_TOOLS.items():
            lines.append(f"  {name}: {info['description']}")
            for pname, pdesc in info.get("parameters", {}).items():
                lines.append(f"    {pname}: {pdesc}")
        return "\n".join(lines)

    def _create_plan(self, goal: str) -> Optional[Plan]:
        messages = [
            Message("system", SYSTEM_PLAN_PROMPT),
            Message("user", f"Create a plan for: {goal}"),
        ]
        response = self.client.complete(messages)
        if response.usage:
            self.prompt_tokens += response.usage.prompt_tokens
            self.completion_tokens += response.usage.completion_tokens
        return extract_plan(response.content, goal)

    def _execute_step(self, step: Step) -> str:
        max_attempts = 5
        for attempt in range(max_attempts):
            if attempt > 0:
                self._emit(f"\033[33m  Retry {attempt}/{max_attempts}\033[0m")

            memory_context = self.memory.retrieve_context(
                f"Step {step.id}: {step.description}", max_tokens=3000
            )
            step_prompt = (
                f"Execute step {step.id}: {step.description}\n"
                f"Previous results: {step.result or 'none'}\n"
                f"Memory context:\n{memory_context}"
            )
            messages = self.history + [Message("user", step_prompt)]
            response = self.client.complete(messages)
            if response.usage:
                self.prompt_tokens += response.usage.prompt_tokens
                self.completion_tokens += response.usage.completion_tokens
            content = response.content.strip()

            self.memory.save_interaction(
                "assistant", content, importance=0.5,
                tags=["step_attempt", f"attempt_{attempt + 1}"]
            )

            action = self._parse_action(content)
            if action is None:
                self.history.append(Message("assistant", content))
                continue

            if action.get("complete"):
                self.history.append(Message("assistant", content))
                result = action.get("result", "Task completed")
                self.memory.add_relation("Pyron", "completed", step.description,
                                         {"result": result[:100]})
                return result

            tool_name = action.get("tool", "")
            params = action.get("parameters", {})

            if tool_name not in AVAILABLE_TOOLS:
                self._emit(f"\033[31m  Unknown tool: {tool_name}\033[0m")
                self.history.append(Message("assistant", content))
                self.history.append(Message("user", f"Unknown tool: {tool_name}"))
                continue

            self._emit(f"  \033[93m{tool_name}\033[0m")

            result = execute_tool(tool_name, params)

            if not result.success:
                self._emit(f"  \033[31m{result.error[:200]}\033[0m")
            else:
                out = result.output[:300]
                self._emit(f"  \033[90m{out}\033[0m")

            self._update_status()

            result_text = json.dumps(result.to_dict(), indent=2)
            self.memory.save_interaction(
                "tool", f"{tool_name}: {result_text[:500]}",
                importance=0.5, tags=["tool_use", tool_name]
            )
            self.history.append(Message("assistant", content))
            self.history.append(Message("user", f"Result:\n{result_text}"))
            self.memory.check_and_compress()

        return "Max attempts reached"

    def _parse_action(self, content: str) -> Optional[dict]:
        decoder = json.JSONDecoder()
        idx = content.find('{')
        while idx != -1:
            try:
                obj, end = decoder.raw_decode(content, idx)
                if isinstance(obj, dict):
                    return obj
            except json.JSONDecodeError:
                pass
            idx = content.find('{', idx + 1)
        return None

    def _summarize(self) -> str:
        if not self.plan:
            return "No plan executed."
        steps_summary = []
        completed = 0
        for step in self.plan.steps:
            status = "done" if step.status == "done" else "failed"
            if step.status == "done":
                completed += 1
            steps_summary.append(f"  {step.id}. {step.description} [{status}]")
        stats = self.memory.get_stats()
        mem = (
            f"memory: {stats['vector_items']} vectors, "
            f"{stats['kg_entities']} entities, "
            f"{stats['kg_relations']} relations"
        )
        tokens = (
            f"tokens: \u2191{self.prompt_tokens} prompt, "
            f"\u2193{self.completion_tokens} completion"
        )
        return (
            f"Goal: {self.plan.goal}  |  "
            f"{completed}/{len(self.plan.steps)} steps  |  "
            f"{mem}  |  {tokens}"
        )
