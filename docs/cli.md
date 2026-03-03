# CLI Usage

The CLI entrypoint is `maf` (from `pyproject.toml`) or `python3 -m maf.cli`.

## `maf run`

Execute one runtime session.

```bash
maf run --input "Hello" --provider mock
```

Key flags:
- `--input` required user input.
- `--provider` `mock|openai|cerebras`.
- `--model` model id (provider defaults: `mock-model`, `gpt-4.1-mini`, `zai-glm-4.7`).
- `--trace-dir` output directory for run artifacts.
- `--max-steps` step budget.
- `--max-run-seconds` wall-clock budget.
- `--stream-events` print structured events live.
- `--disable-power-tools` run with no built-in tools.

Output format:
- `run_id=<id>`
- `status=completed|halted`
- optional `halt_reason=<reason>`
- `final_output=<text>`

## `maf trace`

Print persisted events for one run.

```bash
maf trace --run-id <run_id>
```

You can override artifact location with `--trace-dir`.

## `maf replay`

Replay prior model actions and tool results from an existing run trace.

```bash
maf replay --run-id <run_id>
```

Notes:
- Default replay input comes from the original run metadata.
- Use `--input` to override.
- Replayed tool events include `"replayed": true` in `tool_result` payload.

## Practical Flows

Mock quick flow:

```bash
maf run --provider mock --input "Summarize runtime"
```

OpenAI flow:

```bash
set -a; source .env; set +a
maf run --provider openai --model gpt-4.1-mini --input "Say hello"
```

Cerebras flow:

```bash
set -a; source .env; set +a
maf run --provider cerebras --model zai-glm-4.7 --input "Say hello"
```

Replay flow:

```bash
maf replay --run-id <previous_run_id>
```
