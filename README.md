# Minimal Agent Framework (MAF)

MAF is a small, explicit, replayable agent runtime.

It is intentionally minimal:
- One runtime loop.
- Typed tools with schema validation.
- Persisted traces and state snapshots.
- Replay from recorded model actions and tool results.
- A small CLI (`run`, `trace`, `replay`).

## Current Scope

This repository implements the v0.1 MVP described in [PRD.md](./PRD.md):
- Runtime loop with budgets and halt reasons.
- Mock and OpenAI adapters.
- Core power tools (`shell.exec`, `fs`, `http.fetch`, `kv.get`, `kv.set`).
- JSONL trace persistence and replay.
- Deterministic golden-trace harness.

## Quickstart

### 1. Prerequisites

- Python `>=3.10`
- `pip`

### 2. Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 3. Configure environment

```bash
cp .env.example .env
# edit .env and set OPENAI_API_KEY if using --provider openai
set -a
source .env
set +a
```

### 4. Run with mock provider

```bash
maf run --provider mock --input "Summarize this runtime in one line"
```

### 5. Run with OpenAI provider

```bash
maf run --provider openai --model gpt-4.1-mini --input "Say hello from MAF"
```

### 6. Inspect trace

```bash
maf trace --run-id <run_id>
```

### 7. Replay a prior run

```bash
maf replay --run-id <run_id>
```

## CLI Surface

- `maf run`: executes a run and prints `run_id`, status, and final output.
- `maf trace`: prints persisted trace events for a run.
- `maf replay`: replays model actions and recorded tool outputs from a prior run.

See full flags and examples in [docs/cli.md](./docs/cli.md).

## Python API (Library Use)

```python
from maf import AgentRuntime, RuntimeConfig, MockAdapter, build_power_tools

config = RuntimeConfig(provider="mock", model="mock-model", trace_dir=".maf/runs")
runtime = AgentRuntime(config=config, llm_adapter=MockAdapter(), tools=build_power_tools(config))
result = runtime.run("Explain what you are")

print(result.run_id)
print(result.final_output)
print(result.halt_reason)
```

## Observability and Artifacts

By default each run is stored in `<trace_dir>/<run_id>/`:
- `trace.jsonl`
- `metadata.json`
- `state.initial.json`
- `state.final.json`

See [docs/tracing-and-replay.md](./docs/tracing-and-replay.md).

## Testing and Validation

Run all tests:

```bash
python3 -m unittest discover -s tests -v
```

Run golden trace validator:

```bash
python3 scripts/validate_golden_traces.py
```

See [docs/testing.md](./docs/testing.md).

## Documentation Map

- [Architecture](./docs/architecture.md)
- [API Reference](./docs/api-reference.md)
- [Configuration](./docs/configuration.md)
- [CLI Usage](./docs/cli.md)
- [Tool Contracts](./docs/tools.md)
- [Tracing and Replay](./docs/tracing-and-replay.md)
- [Testing](./docs/testing.md)
- [Cancellation Behavior](./docs/cancellation.md)
- [Troubleshooting](./docs/troubleshooting.md)

## Safety Notes

- `shell.exec` runs local shell commands. Use `RuntimeConfig.tool_allowlist` if you need stricter control.
- `fs` operations are restricted to `RuntimeConfig.fs_root_path`.
- `http.fetch` is deny-by-default unless `MAF_HTTP_ALLOWLIST` is set.
- `.env` is ignored by git in this repository.
