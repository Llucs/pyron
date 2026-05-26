import json
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Optional

from pyron.config import get_api_config


@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class ApiResponse:
    content: str
    model: Optional[str] = None
    usage: Optional[TokenUsage] = None


@dataclass
class Message:
    role: str
    content: str


class ApiClient:
    def __init__(self):
        cfg = get_api_config()
        self.base_url = cfg["base_url"]
        self.model = cfg["model"]
        self.api_key = cfg["api_key"]

    def complete(self, messages: list[Message]) -> ApiResponse:
        payload = json.dumps({
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
        }).encode()

        req = urllib.request.Request(
            self.base_url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": "Pyron/1.0",
            },
            method="POST",
        )

        text = self._execute_with_retry(req)
        obj = json.loads(text)

        if "error" in obj:
            raise RuntimeError(obj["error"])

        model_name = obj.get("model") or None
        usage_data = obj.get("usage")
        usage = None
        if usage_data:
            usage = TokenUsage(
                prompt_tokens=usage_data.get("prompt_tokens", 0),
                completion_tokens=usage_data.get("completion_tokens", 0),
                total_tokens=usage_data.get("total_tokens", 0),
            )

        choices = obj.get("choices", [])
        if choices:
            msg = choices[0].get("message", {})
            content = msg.get("content", "")
            return ApiResponse(content, model_name, usage)

        raise RuntimeError("Invalid response: no choices")

    def _execute_with_retry(self, req: urllib.request.Request, max_retries: int = 3) -> str:
        last_exception = None
        for attempt in range(1, max_retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=120) as resp:
                    text = resp.read().decode()
                    if not text:
                        raise RuntimeError("Empty response")
                    return text
            except (urllib.error.URLError, urllib.error.HTTPError, RuntimeError) as e:
                last_exception = e
                if attempt < max_retries:
                    time.sleep(attempt * 0.8)
        raise last_exception or RuntimeError("Request failed")
