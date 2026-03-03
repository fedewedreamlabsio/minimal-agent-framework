# Architecture

MAF is designed around explicit control flow and explicit state.

## Core Components

- `AgentRuntime`: orchestrates the step loop and enforces control decisions.
- `LLMAdapter`: provider abstraction that returns structured actions.
- `ToolRegistry`: typed set of tool contracts (`ToolSpec`).
- `JsonlRunStore`: persistence layer for traces, metadata, and state snapshots.

Primary implementation files:
- `maf/runtime.py`
- `maf/llm.py`
- `maf/tooling.py`
- `maf/store.py`
- `maf/contracts.py`

## Runtime Loop

The runtime loop follows this sequence:

1. Initialize run state and emit `run_started`.
2. For each step until budget exhaustion:
   - Emit `model_called`.
   - Call adapter for an `Action`.
   - Emit `model_output`.
   - Handle one of:
     - `final`: finalize output and stop.
     - `continue`: update scratch and continue.
     - `tool_call`: validate input schema, execute or replay tool result, validate output schema.
3. Emit `run_finished`.
4. Persist final state + metadata.

## Runtime Ownership vs Model Suggestions

The model proposes actions only. The runtime decides whether they are valid and executable.

Examples of runtime-enforced checks:
- Unknown tool rejection.
- Tool allowlist enforcement.
- Input/output schema validation.
- Max steps and max runtime budget enforcement.
- Replay tool-result availability checks.

## Data Flow

- Input: user text + optional incoming `AgentState`.
- Internal: step events and optional tool executions.
- Output: `RunResult` containing `final_output`, final `state`, in-memory `trace`, and optional `halt_reason`.
- Persisted artifacts: JSONL trace, metadata, state snapshots.

## State Model

`AgentState` fields:
- `thread_id`
- `messages`
- `scratch`
- `artifacts`
- `vars`
- `budgets`

State is explicit: passed into `run()`, mutated through the loop, and returned at the end.

## Error and Halt Semantics

Common halt reasons:
- `max_runtime_seconds`
- `max_steps`
- `cancelled`
- `unknown_tool`
- `tool_not_allowed`
- `tool_input_validation_failed`
- `tool_output_validation_failed`
- `tool_failed`
- `replay_mismatch`
- `invalid_action`

Runtime status in `run_finished` is `completed` when `halt_reason` is null, otherwise `halted`.

## Extension Points

- Add providers: implement the `LLMAdapter` protocol.
- Add tools: create `ToolSpec` and register with runtime.
- Replace store: pass a custom store implementation compatible with runtime usage.
- Add policy layer: intercept/validate actions before execution.
