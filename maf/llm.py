from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from .contracts import Action, AgentState, JsonDict, ModelResult, RuntimeConfig, ToolSpec


class AdapterError(RuntimeError):
    pass


def action_from_dict(data: JsonDict) -> Action:
    action_type = str(data.get("type", "")).strip()
    if action_type not in {"final", "tool_call", "continue"}:
        raise AdapterError(f"invalid action type: {action_type!r}")

    return Action(
        type=action_type,
        final_output=data.get("final_output"),
        tool_name=data.get("tool_name"),
        tool_input=data.get("tool_input") if isinstance(data.get("tool_input"), dict) else {},
        internal_note=data.get("internal_note"),
    )


def parse_action_json(text: str) -> Action:
    candidate = text.strip()
    if candidate.startswith("```"):
        candidate = _strip_code_fences(candidate)

    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise AdapterError(f"unable to parse action JSON: {exc}") from exc

    if not isinstance(parsed, dict):
        raise AdapterError("parsed action payload must be an object")
    return action_from_dict(parsed)


def _strip_code_fences(text: str) -> str:
    pattern = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", flags=re.DOTALL)
    match = pattern.match(text.strip())
    return match.group(1) if match else text


@dataclass
class MockAdapter:
    scripted_actions: list[Action] | None = None

    def __post_init__(self) -> None:
        self._queue = list(self.scripted_actions or [])

    def complete(
        self,
        *,
        run_id: str,
        step_index: int,
        state: AgentState,
        tools: list[ToolSpec],
        config: RuntimeConfig,
    ) -> ModelResult:
        del run_id, step_index, tools, config
        if self._queue:
            return ModelResult(action=self._queue.pop(0))

        last_user_message = ""
        for message in reversed(state.messages):
            if message.get("role") == "user":
                last_user_message = str(message.get("content", ""))
                break

        return ModelResult(action=Action(type="final", final_output=f"Echo: {last_user_message}"))


@dataclass
class OpenAIChatAdapter:
    model: str = "gpt-4.1-mini"
    timeout_seconds: float = 30.0
    endpoint: str = "https://api.openai.com/v1/chat/completions"
    api_key: str | None = None

    def complete(
        self,
        *,
        run_id: str,
        step_index: int,
        state: AgentState,
        tools: list[ToolSpec],
        config: RuntimeConfig,
    ) -> ModelResult:
        del run_id, step_index, config
        api_key = self.api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise AdapterError("OPENAI_API_KEY is required for OpenAIChatAdapter")

        prompt_payload = {
            "state": state.as_dict(),
            "tools": [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.input_schema,
                }
                for tool in tools
            ],
            "contract": {
                "instruction": "Reply with JSON action only.",
                "types": ["final", "tool_call", "continue"],
                "schema": {
                    "type": "object",
                    "required": ["type"],
                    "properties": {
                        "type": {"enum": ["final", "tool_call", "continue"]},
                        "final_output": {"type": "string"},
                        "tool_name": {"type": "string"},
                        "tool_input": {"type": "object"},
                        "internal_note": {"type": "string"},
                    },
                },
            },
        }

        body = {
            "model": self.model,
            "temperature": 0,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are an agent policy engine. Output exactly one JSON object that matches "
                        "the action contract. Do not include prose or markdown."
                    ),
                },
                {"role": "user", "content": json.dumps(prompt_payload, sort_keys=True)},
            ],
        }

        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                response_body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:  # pragma: no cover - network-dependent
            raw = exc.read().decode("utf-8", errors="replace")
            raise AdapterError(f"openai http error: {exc.code} {raw}") from exc
        except urllib.error.URLError as exc:  # pragma: no cover - network-dependent
            raise AdapterError(f"openai connection error: {exc}") from exc

        decoded: JsonDict = json.loads(response_body)
        content = _extract_chat_content(decoded)
        action = parse_action_json(content)
        usage = decoded.get("usage", {}) if isinstance(decoded, dict) else {}
        usage_dict = usage if isinstance(usage, dict) else {}
        return ModelResult(action=action, raw_text=content, usage=usage_dict)


def _extract_chat_content(response_json: JsonDict) -> str:
    try:
        choices = response_json["choices"]
        first = choices[0]
        message = first["message"]
        content = message["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise AdapterError("unexpected OpenAI response format") from exc

    if not isinstance(content, str):
        raise AdapterError("OpenAI response content is not a string")
    return content
