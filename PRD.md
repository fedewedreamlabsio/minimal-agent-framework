# Minimal Agent Framework (MAF)
Beads Epic: agent-s44

## Problem
Modern agent frameworks are often too abstract, dependency-heavy, and difficult to debug. Teams lose confidence because control flow, tool semantics, and state mutation are hidden behind framework magic. We need a minimal runtime that is easy to reason about, replay, and own end-to-end.

## Goals
- Deliver a first-principles agent kernel loop that can be explained in under 60 seconds.
- Keep tool calling deterministic with explicit runtime validation and failure semantics.
- Make state explicit and portable across runs.
- Persist traces/state so runs are inspectable and replayable.
- Provide a small CLI surface for run, trace, and replay.
- Stay provider-agnostic with a pluggable LLM adapter.

## Non-Goals
- Multi-agent orchestration or swarm scheduling.
- Complex memory/RAG orchestration in v0.1.
- Enterprise-grade authz/compliance controls in v0.1.
- Visual workflow builders or GUI studios.
- Background autonomous long-running workers in v0.1.

## Users
- Primary: engineers building production-ish agents with low lock-in and high debuggability.
- Secondary: operators troubleshooting run failures via local traces and replay.

## Success Metrics
- `<= 1` command to run a local agent example from a clean clone.
- `100%` of runtime steps produce structured trace events.
- `100%` of tool invocations enforce timeout and schema validation.
- Replay command can reproduce control-flow decisions using recorded tool outputs.
- Core runtime remains auditable in roughly `500-1500` LOC (excluding tests/examples).

## Scope
- In scope:
  - Step-based runtime loop: read, think, decide, act, write, repeat.
  - Typed tool registry with schema validation and timeout handling.
  - Trace emission and persistence (JSONL first).
  - Final state persistence and optional per-step snapshots.
  - CLI commands: `maf run`, `maf trace`, `maf replay`.
  - Minimal state model: messages, scratch, artifacts, vars, budgets.
- Out of scope:
  - Parallel tool fanout in v0.1.
  - Advanced policy engine beyond basic allowlist/limits.
  - Hosted control plane or multi-tenant SaaS concerns.

## Prerequisites (Keys, Access, CLIs)
- Required secrets/keys:
  - `OPENAI_API_KEY` (required when OpenAI adapter is selected).
  - `ANTHROPIC_API_KEY` (required when Anthropic adapter is selected).
  - `MAF_HTTP_ALLOWLIST` (strict comma-separated host allowlist for `http.fetch`).
  - `E2E_BYPASS_TOKEN` (only if preview environments are access-protected).
- Required services/accounts:
  - At least one LLM provider account (OpenAI or Anthropic initially).
  - Source control access for reproducible traces and CI wiring.
  - Optional preview host account (if web playground or remote demos are added).
- Required CLI tools:
  - `git`
  - `bd` (beads issue tracking)
  - Language toolchain (to be decided: Go, Rust, Python, or Node)
  - `make` (or task runner equivalent) for one-command local workflows
  - `railway` CLI (required only for deploy workflows; run `railway login` + `railway link` first)
  - Playwright deps for browser/E2E checks when applicable:
    - `python -m playwright install`
    - Linux runners: `python -m playwright install-deps` (or equivalent system packages)
- E2E/preview access plan (if SSO/protection is enabled):
  - Prefer local-first E2E against localhost.
  - If preview protection is enabled, use either:
    - an approved custom domain bypass,
    - an explicit bypass header/token in CI,
    - or temporary protection disablement approved by project owners.

## User Stories / JTBD
- As an engineer, I can run a prompt through the agent loop and receive a final answer with a full trace.
- As an engineer, I can register a typed tool and have runtime-enforced schema validation before execution.
- As an operator, I can inspect a run trace and understand each decision/action event in order.
- As a developer, I can replay a prior run using recorded tool results to debug regressions.
- As a developer, I can halt runaway loops with max-step/time budgets and clear halt reasons.

## UX / Flow Notes
- Primary flow is CLI-first:
  - `maf run --input "..."`
  - `maf trace --run-id <id>`
  - `maf replay --run-id <id>`
- Event-stream output should favor deterministic high-level events first; token streaming can be optional later.
- Debug view should make step boundaries and tool inputs/outputs obvious.

## Technical Constraints
- Runtime owns control flow; model only proposes actions.
- Tool contracts must be typed and validated (schema in/out).
- Retries/timeouts are explicit, configurable, and trace-recorded.
- State is passed and returned; avoid hidden mutable globals.
- Core dependencies must stay minimal and justified.

## Risks & Open Questions
- Language choice tradeoff (Go/Rust/Python/Node) impacts binary portability, dev speed, and dependency profile.
- JSONL vs SQLite for trace store in v0.1 may impact replay ergonomics and query performance.
- Prompt/action contract strictness: strict JSON schema vs tolerant parser + validator.
- History policy may require truncation/summarization to avoid context explosion.
- Determinism is best-effort due to model nondeterminism; replay mode should isolate tool nondeterminism first.

## Functional Requirements
- FR1 Agent loop:
  - System SHALL execute a step-based loop ending in `final` or explicit halt reason.
  - System SHALL produce a `RunTrace` with structured events for each step.
- FR2 Tool calls:
  - System SHALL maintain tool registry entries with name, description, input schema, output schema, timeout.
  - System SHALL validate tool inputs before execution and record validation failures.
  - System SHALL record tool call input/output/error in the trace.
- FR3 State handling:
  - System SHALL accept input state and return updated state.
  - System SHALL persist final state and run metadata.
- FR4 Observability:
  - System SHALL emit `run_started`, `model_called`, `tool_called`, `tool_result`, `run_finished`, and `error`.
  - System SHALL provide CLI trace inspection by run id.
- FR5 Configuration:
  - System SHALL configure provider/model, max steps, time budgets, runtime timeouts, and tool allowlist.

## Non-Functional Requirements
- NFR1 Minimalism:
  - v0.1 core runtime is auditable in approximately `500-1500` LOC.
  - Dependencies remain intentionally small and documented.
- NFR2 Reliability:
  - Tool calls enforce timeouts and explicit error semantics.
  - Retries, if enabled, are explicit and trace-recorded.
- NFR3 Performance:
  - Trace emission overhead should remain low relative to model/tool latency.
  - Event streaming should not block tool execution.
- NFR4 Determinism (best-effort):
  - Given same inputs, state, tool outputs (or replay), and model settings, control-flow is reproducible.

## Data Model (Seed)
- RunTrace event:
  - `run_id`
  - `ts`
  - `type`
  - `payload`
- State object:
  - `thread_id`
  - `messages[]`
  - `scratch`
  - `artifacts[]`
  - `vars` (kv map)
  - `budgets` (steps/time/tokens)

## API Surface (Seed)
- Library:
  - `runtime = AgentRuntime(config, tools, llm_adapter, store)`
  - `result = runtime.run(input, state=None)`
  - `result.final_output`
  - `result.state`
  - `result.trace`
- CLI:
  - `maf run --input "..."`
  - `maf replay --run-id ...`
  - `maf trace --run-id ...`

## Milestones
- M1: Runtime skeleton + final-only model response path.
- M2: Tool registry + `shell.exec` tool + schema validation.
- M3: JSONL trace persistence + debug trace viewer command.
- M4: Replay mode using recorded tool results.
- M5: CLI polish + event streaming + docs/examples.

## Acceptance Criteria (MVP)
1. Register `3-6` tools and invoke at least one from runtime.
2. Execute loop where model proposes tool call, runtime validates/executes, and final output is returned.
3. Persist and inspect run trace locally via CLI.
4. Enforce and record tool timeouts.
5. Run locally with minimal setup and a single command.
