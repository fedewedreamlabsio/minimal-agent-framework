# Minimal Agent Framework (MAF)

A small, auditable, replayable agent runtime. One loop. Typed tools. Full traces. Nothing else.

## Why MAF?

Every agent framework wants to be everything. MAF wants to be *understood*.

- **One runtime loop** — read the source in 15 minutes
- **Typed tools** with input/output schema validation
- **JSONL traces** on every run — replay, debug, audit
- **Any OpenAI-compatible model** — OpenAI, Cerebras, Gemini, Groq, local models
- **Sandboxed by default** — fs root boundaries, HTTP allowlists, tool allowlists

## Quickstart

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
```

### Mock (no API key needed)

```bash
maf run --provider mock --input "Hello from MAF"
```

### OpenAI

```bash
export OPENAI_API_KEY="sk-..."
maf run --provider openai --input "List files in the current directory"
```

### Any OpenAI-compatible provider (Gemini, Groq, etc.)

```bash
maf run \
  --provider openai \
  --endpoint "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions" \
  --api-key "$GEMINI_API_KEY" \
  --model gemini-2.5-flash \
  --input "List files and summarize what you find"
```

## Real-World Example: Autonomous KPI Analysis

This is how we actually use MAF — delegating a multi-step analytics task that calls external CLIs, processes the results, and writes a report:

```bash
maf run \
  --provider openai \
  --endpoint "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions" \
  --api-key "$GEMINI_API_KEY" \
  --model gemini-2.5-flash \
  --max-steps 12 \
  --input 'Gather site traffic data and write a KPI report.
    Step 1: Run shell command: datafast overview --period 30d --json
    Step 2: Run shell command: datafast top referrers --period 30d --json
    Step 3: Write file kpi-report.md with metrics summary and recommendations.
    Step 4: Return the report as final output.'
```

MAF executes each step autonomously — calling `shell.exec`, processing JSON output, writing the report via `fs`, and returning the result. Every step is traced in JSONL.

Related operator writeups:
- [Datafast CLI for AI Agent Tools: Workflow, Artifacts, Handoffs](https://starkslab.com/notes/ai-developer-tools-datafast-cli-workflow)
- [SEO CLI for AI Developer Tools: SERPs, Audits, Handoffs](https://starkslab.com/notes/ai-developer-tools-seo-cli-workflow)

```
[09:27:01] run_started    provider=gemini, model=gemini-2.5-flash, max_steps=12
[09:27:02] tool_called    shell.exec → datafast overview --period 30d --json
[09:27:03] tool_result    ✓ exit_code=0, 26 visitors, 66.67% bounce rate
[09:27:05] tool_called    shell.exec → datafast top referrers --period 30d --json
[09:27:06] tool_result    ✓ exit_code=0, Direct: 16, X: 7, Google: 3
[09:27:07] tool_called    shell.exec → datafast top pages --period 30d --json
[09:27:08] tool_result    ✓ exit_code=0, 10 pages returned
[09:27:20] tool_called    fs.write → kpi-report.md (2,006 bytes)
[09:27:25] run_finished   status=completed, 5 steps, ~24 seconds
```

## Built-in Tools

| Tool | Purpose | Safety |
|------|---------|--------|
| `shell.exec` | Run shell commands | `cwd` constrained to `fs_root_path` |
| `fs` | Read, write, list files | Paths must stay under `fs_root_path` |
| `http.fetch` | HTTP requests | Deny-by-default, URL allowlist required |
| `kv` | Key-value persistence | File-backed, scoped to run config |

## CLI

```bash
maf run      # Execute a run
maf trace    # Inspect persisted trace events
maf replay   # Replay a prior run from recorded traces
maf perf     # Token throughput metrics
```

Key flags for `maf run`:
- `--provider` — `mock`, `openai`, `cerebras`
- `--model` — model identifier
- `--endpoint` — override API endpoint (for OpenAI-compatible providers)
- `--api-key` — override API key directly
- `--max-steps` / `--max-run-seconds` — budget controls
- `--stream-events` — print structured events live

See [docs/cli.md](./docs/cli.md) for full reference.

## Python API

```python
from maf import AgentRuntime, RuntimeConfig, OpenAIChatAdapter, build_power_tools

config = RuntimeConfig(
    provider="openai",
    model="gpt-4.1-mini",
    max_steps=10,
    max_run_seconds=60,
    trace_dir=".maf/runs",
    fs_root_path="./workspace",
)

adapter = OpenAIChatAdapter(model="gpt-4.1-mini")
tools = build_power_tools(config)
runtime = AgentRuntime(config=config, llm_adapter=adapter, tools=tools)

result = runtime.run("Read all files and create a summary")
print(result.final_output)
```

## Traces & Replay

Every run produces artifacts in `<trace_dir>/<run_id>/`:

```
.maf/runs/4f720ddf/
├── trace.jsonl          # Every event: model calls, tool results, timing
├── metadata.json        # Run config, provider, model, budgets
├── state.initial.json   # Input state snapshot
└── state.final.json     # Output state snapshot
```

Replay any run deterministically:

```bash
maf replay --run-id 4f720ddf
```

## Testing

```bash
python3 -m pytest tests/ -x     # All tests
python3 scripts/validate_golden_traces.py  # Golden trace validation
```

## Docs

- [Architecture](./docs/architecture.md)
- [Configuration](./docs/configuration.md)
- [CLI Reference](./docs/cli.md)
- [Tool Contracts](./docs/tools.md)
- [Tracing & Replay](./docs/tracing-and-replay.md)
- [Testing](./docs/testing.md)
- [API Reference](./docs/api-reference.md)

## License

MIT — see [LICENSE](./LICENSE).
