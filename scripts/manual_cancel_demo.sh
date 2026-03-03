#!/usr/bin/env bash
set -euo pipefail

# Manual check for Ctrl+C cancellation behavior.
# Expected outcome:
# - process exits normally after KeyboardInterrupt is handled by runtime
# - final output shows halt_reason=cancelled
# - partial trace exists under .maf/runs/<run_id>/trace.jsonl
python3 - <<'PY'
import time

from maf import Action, AgentRuntime, ModelResult, RuntimeConfig


class SlowLoopAdapter:
    def complete(self, **_kwargs):
        time.sleep(1.0)
        return ModelResult(action=Action(type="continue", internal_note="tick"))


runtime = AgentRuntime(
    config=RuntimeConfig(trace_dir=".maf/runs", max_steps=999, max_run_seconds=999),
    llm_adapter=SlowLoopAdapter(),
)

print("Press Ctrl+C to cancel the run...")
result = runtime.run("manual-cancel-demo", event_handler=lambda e: print(e["type"], flush=True))
print(f"run_id={result.run_id}")
print(f"halt_reason={result.halt_reason}")
PY
