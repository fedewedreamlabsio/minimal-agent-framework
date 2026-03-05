# API Reference

This page documents the primary public surface exported by `maf/__init__.py`.

## Core Types

### `RuntimeConfig`

Runtime settings object used by `AgentRuntime`.

Key fields:
- `provider`
- `model`
- `max_steps`
- `max_run_seconds`
- `trace_dir`
- `default_tool_timeout_seconds`
- `tool_allowlist`
- `fs_root_path`
- `http_allowlist`
- `kv_store_path`

### `AgentState`

Explicit run state.

Fields:
- `thread_id`
- `messages`
- `scratch`
- `artifacts`
- `vars`
- `budgets`

Helpers:
- `AgentState.from_dict(data)`
- `state.as_dict()`

### `Action`

Structured model decision object.

Fields:
- `type`: `final|tool_call|continue`
- `final_output`
- `tool_name`
- `tool_input`
- `internal_note`

### `ModelResult`

Adapter response wrapper.

Fields:
- `action`
- `raw_text`
- `usage`

### `ToolSpec`

Typed tool contract.

Fields:
- `name`
- `description`
- `input_schema`
- `output_schema`
- `timeout_seconds`
- `handler(payload, state) -> dict`

### `RunResult`

Runtime result object returned by `AgentRuntime.run()`.

Fields:
- `run_id`
- `final_output`
- `state`
- `trace`
- `halt_reason`

## Runtime

### `AgentRuntime`

Constructor:

```python
AgentRuntime(config=RuntimeConfig(...), llm_adapter=..., tools=[...], store=...)
```

Run method:

```python
run(
  input_text: str,
  state: AgentState | None = None,
  replay_tool_results: list[dict] | None = None,
  event_handler: Callable[[dict], None] | None = None,
) -> RunResult
```

Behavior:
- Creates a new run id.
- Emits and persists events.
- Executes step loop until `final` or halt.
- Persists initial/final state snapshots and metadata.

## Adapters

### `MockAdapter`

Deterministic local adapter for testing and development.

### `OpenAIChatAdapter`

OpenAI-backed adapter using `chat/completions` and JSON action contract.

Requirements:
- `OPENAI_API_KEY`

### `CerebrasChatAdapter`

Cerebras-backed adapter using OpenAI-compatible `chat/completions`.

Defaults:
- endpoint: `https://api.cerebras.ai/v1/chat/completions`
- model: `zai-glm-4.7`

Requirements:
- `CEREBRAS_API_KEY`

### `ReplayAdapter`

Constructed from prior trace:

```python
ReplayAdapter.from_trace(trace)
```

Returns model actions in recorded order.

### `AdapterError`

Raised for adapter parsing/provider failures.

## Tools and Registry

### `build_power_tools(config)`

Returns default built-in tool set.

### `ToolRegistry`

Typed registry with duplicate-name protection.

Methods:
- `register(tool)`
- `get(name)`
- `list()`
- `schemas()`

## Store

### `JsonlRunStore`

Persistence utility for run artifacts.

Methods:
- `begin_run(run_id, metadata)`
- `append_event(run_id, event)`
- `save_state(run_id, state, phase="initial|final")`
- `finish_run(run_id, result)`
- `load_trace(run_id)`
- `load_state(run_id, phase="final")`
- `load_metadata(run_id)`
- `list_runs()`
