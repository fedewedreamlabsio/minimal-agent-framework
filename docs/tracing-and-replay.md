# Tracing and Replay

MAF persists runs for observability and deterministic replay.

## Artifact Layout

For each run, files are created in:

`<trace_dir>/<run_id>/`

Files:
- `trace.jsonl`: append-only event stream.
- `metadata.json`: run metadata + final status summary.
- `state.initial.json`: state snapshot before steps.
- `state.final.json`: final state snapshot.

## Event Shape

Each event in `trace.jsonl` is a JSON object:
- `run_id`
- `ts` (UTC ISO timestamp)
- `type`
- `payload`

Common event types:
- `run_started`
- `model_called`
- `model_output`
- `tool_called`
- `tool_result`
- `error`
- `run_finished`

## Replay Mechanics

Replay mode uses two extracted streams from trace:
- Model actions (`model_output.payload.action`)
- Tool result payloads (`tool_result.payload`)

At runtime replay:
- `ReplayAdapter` returns recorded model actions in order.
- `AgentRuntime.run(..., replay_tool_results=...)` injects recorded tool outputs.
- `tool_result` payload includes `"replayed": true`.

## Determinism Notes

Replay isolates nondeterminism from external tools and model sampling.

Remaining variability can still come from:
- Different runtime code version.
- Different validation schemas.
- Different input override (`maf replay --input ...`).

## Trace Inspection

CLI inspection:

```bash
maf trace --run-id <run_id>
```

Programmatic loading:

```python
from maf import JsonlRunStore

store = JsonlRunStore(".maf/runs")
trace = store.load_trace("<run_id>")
metadata = store.load_metadata("<run_id>")
```
