from __future__ import annotations

import json
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from datetime import datetime, timezone
from typing import Callable

from .contracts import AgentState, JsonDict, LLMAdapter, RunResult, RuntimeConfig, ToolSpec
from .schema import validate_json
from .store import JsonlRunStore
from .tooling import ToolRegistry


class AgentRuntime:
    def __init__(
        self,
        *,
        config: RuntimeConfig,
        llm_adapter: LLMAdapter,
        tools: list[ToolSpec] | None = None,
        store: JsonlRunStore | None = None,
    ) -> None:
        self.config = config
        self.llm_adapter = llm_adapter
        self._tools = ToolRegistry(tools)
        self.store = store or JsonlRunStore(config.trace_dir)

    def run(
        self,
        input_text: str,
        *,
        state: AgentState | None = None,
        event_handler: Callable[[JsonDict], None] | None = None,
    ) -> RunResult:
        run_id = uuid.uuid4().hex
        trace: list[JsonDict] = []
        started_at = time.monotonic()

        if state is None:
            state = AgentState(thread_id=f"thread-{run_id[:8]}")

        state.messages.append({"role": "user", "content": input_text})
        self.store.begin_run(
            run_id,
            {
                "run_id": run_id,
                "thread_id": state.thread_id,
                "provider": self.config.provider,
                "model": self.config.model,
                "max_steps": self.config.max_steps,
                "max_run_seconds": self.config.max_run_seconds,
                "input": input_text,
            },
        )
        self.store.save_state(run_id, state, phase="initial")

        def emit(event_type: str, payload: JsonDict) -> None:
            event = {
                "run_id": run_id,
                "ts": datetime.now(timezone.utc).isoformat(),
                "type": event_type,
                "payload": payload,
            }
            trace.append(event)
            self.store.append_event(run_id, event)
            if event_handler is not None:
                event_handler(event)

        emit(
            "run_started",
            {
                "thread_id": state.thread_id,
                "input": input_text,
                "provider": self.config.provider,
                "model": self.config.model,
                "max_steps": self.config.max_steps,
                "max_run_seconds": self.config.max_run_seconds,
            },
        )

        halt_reason: str | None = None
        final_output = ""

        try:
            for step_index in range(self.config.max_steps):
                elapsed = time.monotonic() - started_at
                if elapsed > self.config.max_run_seconds:
                    halt_reason = "max_runtime_seconds"
                    emit(
                        "error",
                        {
                            "step": step_index,
                            "error": "run time budget exceeded",
                            "elapsed_seconds": elapsed,
                        },
                    )
                    break

                state.budgets = {
                    "remaining_steps": self.config.max_steps - step_index,
                    "remaining_seconds": max(0.0, self.config.max_run_seconds - elapsed),
                }

                emit(
                    "model_called",
                    {
                        "step": step_index,
                        "message_count": len(state.messages),
                    },
                )

                model_result = self.llm_adapter.complete(
                    run_id=run_id,
                    step_index=step_index,
                    state=state,
                    tools=self._tools.list(),
                    config=self.config,
                )
                action = model_result.action

                emit(
                    "model_output",
                    {
                        "step": step_index,
                        "action": action.as_dict(),
                        "usage": model_result.usage,
                    },
                )

                if action.type == "final":
                    final_output = action.final_output or ""
                    state.messages.append({"role": "assistant", "content": final_output})
                    halt_reason = None
                    break

                if action.type == "continue":
                    if action.internal_note:
                        state.scratch["last_note"] = action.internal_note
                    continue

                if action.type == "tool_call":
                    tool_name = action.tool_name or ""
                    tool = self._tools.get(tool_name)
                    if tool is None:
                        halt_reason = "unknown_tool"
                        emit(
                            "error",
                            {
                                "step": step_index,
                                "error": f"unknown tool: {tool_name}",
                            },
                        )
                        break

                    if self.config.tool_allowlist and tool_name not in self.config.tool_allowlist:
                        halt_reason = "tool_not_allowed"
                        emit(
                            "error",
                            {
                                "step": step_index,
                                "error": f"tool not in allowlist: {tool_name}",
                            },
                        )
                        break

                    tool_input = action.tool_input or {}
                    validation_errors = validate_json(tool_input, tool.input_schema)
                    if validation_errors:
                        halt_reason = "tool_input_validation_failed"
                        emit(
                            "error",
                            {
                                "step": step_index,
                                "tool_name": tool.name,
                                "error": "tool input schema validation failed",
                                "validation_errors": validation_errors,
                            },
                        )
                        break

                    emit(
                        "tool_called",
                        {
                            "step": step_index,
                            "tool_name": tool.name,
                            "input": tool_input,
                        },
                    )

                    tool_result, tool_error = self._execute_tool(tool, tool_input, state)
                    emit(
                        "tool_result",
                        {
                            "step": step_index,
                            "tool_name": tool.name,
                            "output": tool_result,
                            "error": tool_error,
                        },
                    )

                    if tool_error is not None:
                        halt_reason = "tool_failed"
                        break

                    output_validation_errors = validate_json(tool_result, tool.output_schema)
                    if output_validation_errors:
                        halt_reason = "tool_output_validation_failed"
                        emit(
                            "error",
                            {
                                "step": step_index,
                                "tool_name": tool.name,
                                "error": "tool output schema validation failed",
                                "validation_errors": output_validation_errors,
                            },
                        )
                        break

                    state.messages.append(
                        {
                            "role": "tool",
                            "name": tool.name,
                            "content": json.dumps(tool_result, sort_keys=True),
                        }
                    )
                    continue

                halt_reason = "invalid_action"
                emit(
                    "error",
                    {
                        "step": step_index,
                        "error": f"invalid action type: {action.type}",
                    },
                )
                break
            else:
                halt_reason = "max_steps"
                emit(
                    "error",
                    {
                        "step": self.config.max_steps,
                        "error": "max step budget reached",
                    },
                )
        except KeyboardInterrupt:
            halt_reason = "cancelled"
            emit("error", {"error": "run cancelled by user"})

        status = "completed" if halt_reason is None else "halted"
        emit(
            "run_finished",
            {
                "status": status,
                "halt_reason": halt_reason,
                "final_output": final_output,
                "message_count": len(state.messages),
            },
        )
        self.store.save_state(run_id, state, phase="final")
        self.store.finish_run(
            run_id,
            {
                "status": status,
                "halt_reason": halt_reason,
                "final_output": final_output,
                "events": len(trace),
            },
        )

        return RunResult(
            run_id=run_id,
            final_output=final_output,
            state=state,
            trace=trace,
            halt_reason=halt_reason,
        )

    def _execute_tool(
        self,
        tool: ToolSpec,
        tool_input: JsonDict,
        state: AgentState,
    ) -> tuple[JsonDict, str | None]:
        timeout = tool.timeout_seconds or self.config.default_tool_timeout_seconds
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(tool.handler, tool_input, state)
            try:
                return future.result(timeout=timeout), None
            except FutureTimeout:
                return {"timed_out": True}, f"tool timeout ({timeout}s)"
            except Exception as exc:  # pragma: no cover - defensive path
                return {"exception": type(exc).__name__}, str(exc)
