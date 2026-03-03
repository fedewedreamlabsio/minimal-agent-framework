from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

JsonDict = dict[str, Any]


@dataclass
class Action:
    type: str
    final_output: str | None = None
    tool_name: str | None = None
    tool_input: JsonDict | None = None
    internal_note: str | None = None

    def as_dict(self) -> JsonDict:
        return {
            "type": self.type,
            "final_output": self.final_output,
            "tool_name": self.tool_name,
            "tool_input": self.tool_input,
            "internal_note": self.internal_note,
        }


@dataclass
class ModelResult:
    action: Action
    raw_text: str | None = None
    usage: JsonDict = field(default_factory=dict)


@dataclass
class AgentState:
    thread_id: str
    messages: list[JsonDict] = field(default_factory=list)
    scratch: JsonDict = field(default_factory=dict)
    artifacts: list[str] = field(default_factory=list)
    vars: JsonDict = field(default_factory=dict)
    budgets: JsonDict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: JsonDict) -> "AgentState":
        return cls(
            thread_id=str(data.get("thread_id", "")),
            messages=list(data.get("messages", [])),
            scratch=dict(data.get("scratch", {})),
            artifacts=list(data.get("artifacts", [])),
            vars=dict(data.get("vars", {})),
            budgets=dict(data.get("budgets", {})),
        )

    def as_dict(self) -> JsonDict:
        return {
            "thread_id": self.thread_id,
            "messages": self.messages,
            "scratch": self.scratch,
            "artifacts": self.artifacts,
            "vars": self.vars,
            "budgets": self.budgets,
        }


@dataclass
class RuntimeConfig:
    provider: str = "mock"
    model: str = "mock-model"
    max_steps: int = 12
    max_run_seconds: float = 90.0
    default_tool_timeout_seconds: float = 10.0
    tool_allowlist: list[str] | None = None


ToolHandler = Callable[[JsonDict, AgentState], JsonDict]


@dataclass
class ToolSpec:
    name: str
    description: str
    input_schema: JsonDict
    output_schema: JsonDict
    timeout_seconds: float
    handler: ToolHandler


class LLMAdapter(Protocol):
    def complete(
        self,
        *,
        run_id: str,
        step_index: int,
        state: AgentState,
        tools: list[ToolSpec],
        config: RuntimeConfig,
    ) -> ModelResult:
        ...


@dataclass
class RunResult:
    run_id: str
    final_output: str
    state: AgentState
    trace: list[JsonDict]
    halt_reason: str | None = None
