# Cancellation Behavior

Run this script and press `Ctrl+C` while events are streaming:

```bash
bash scripts/manual_cancel_demo.sh
```

Expected behavior:
- Runtime emits `error` with cancellation message.
- Runtime emits `run_finished` with `status=halted` and `halt_reason=cancelled`.
- Partial trace is persisted at `.maf/runs/<run_id>/trace.jsonl`.
- Final state snapshot is persisted at `.maf/runs/<run_id>/state.final.json`.
