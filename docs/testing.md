# Testing

MAF uses `unittest` plus a golden-trace regression harness.

## Run Everything

```bash
python3 -m unittest discover -s tests -v
python3 scripts/validate_golden_traces.py
```

## Test Areas

- Runtime control loop and halt conditions.
- Adapter parsing and provider key requirements.
- Tool registry and schema validation.
- Power tool behavior (`shell`, `fs`, `http`, `kv`).
- Trace persistence and metadata/state snapshots.
- Replay behavior (tool outputs reused, no re-execution).
- CLI integration path (`run`, `trace`, `replay`).
- Streaming and cancellation behavior.

## Golden Traces

Script:
- `scripts/validate_golden_traces.py`

Scenarios:
- `final_only`
- `tool_success`
- `tool_timeout`

Fixtures live in:
- `tests/golden/*.json`

Refresh fixtures intentionally:

```bash
python3 scripts/validate_golden_traces.py --update
```

Use refresh only when behavior changes are expected and reviewed.
