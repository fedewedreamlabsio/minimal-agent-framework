# Troubleshooting

## `OPENAI_API_KEY is required for OpenAIChatAdapter`

Cause:
- Key is missing from environment in current shell.

Fix:

```bash
set -a
source .env
set +a
```

Verify:

```bash
python3 - <<'PY'
import os
print('set' if os.getenv('OPENAI_API_KEY') else 'missing')
PY
```

## `no trace found for run_id=...`

Cause:
- Wrong `run_id` or wrong `--trace-dir`.

Fix:
- Confirm trace dir used in run command.
- Confirm run folder exists under that directory.

## `tool input schema validation failed`

Cause:
- Model produced payload that does not match tool schema.

Fix:
- Inspect `model_output` and `error` events with `maf trace`.
- Tighten prompt contract or update tool schema.

## `tool output schema validation failed`

Cause:
- Tool handler returned unexpected shape.

Fix:
- Align handler return value with `ToolSpec.output_schema`.
- Add/adjust tests for tool output format.

## `url is not allowed by MAF_HTTP_ALLOWLIST`

Cause:
- `http.fetch` URL prefix not in allowlist.

Fix:

```bash
export MAF_HTTP_ALLOWLIST="https://api.github.com,https://httpbin.org"
```

## `path escapes configured fs root`

Cause:
- `fs` or `shell.exec` `cwd` attempts to read outside `fs_root_path`.

Fix:
- Use a relative path inside root.
- Explicitly set `RuntimeConfig.fs_root_path` if needed.

## Replay stops with `replay_mismatch`

Cause:
- Replay consumed fewer or more tool calls than current action sequence.

Fix:
- Replay against the exact trace from original run.
- Avoid changing core runtime/tool-action behavior before replaying.
- Re-run baseline and replay from fresh trace.

## Run halts with `max_steps` or `max_runtime_seconds`

Cause:
- Task is not converging within budget.

Fix:
- Increase `--max-steps` and/or `--max-run-seconds`.
- Improve prompt/action contract to reduce unnecessary `continue` loops.
