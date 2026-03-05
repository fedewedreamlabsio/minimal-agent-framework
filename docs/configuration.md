# Configuration

MAF configuration comes from `RuntimeConfig` and select environment variables.

## RuntimeConfig Fields

Defined in `maf/contracts.py`.

- `provider`: provider label used for metadata (`mock`, `openai`, `cerebras`, `replay`, etc.).
- `model`: model name identifier.
- `max_steps`: max number of loop iterations.
- `max_run_seconds`: wall-clock run budget.
- `trace_dir`: base directory for run artifacts.
- `default_tool_timeout_seconds`: fallback tool timeout.
- `tool_allowlist`: optional list of allowed tool names.
- `fs_root_path`: root directory boundary for `fs` and `shell.exec` cwd resolution.
- `http_allowlist`: URL-prefix allowlist for `http.fetch`.
- `kv_store_path`: path for `kv` persistence.

## Environment Variables

- `OPENAI_API_KEY`: required for `--provider openai`.
- `CEREBRAS_API_KEY`: required for `--provider cerebras`.
- `MAF_HTTP_ALLOWLIST`: comma-separated URL prefixes for `http.fetch`.

Example:

```bash
export OPENAI_API_KEY="sk-..."
export CEREBRAS_API_KEY="csk-..."
export MAF_HTTP_ALLOWLIST="https://api.github.com,https://httpbin.org"
```

## .env Usage

This project does not auto-load `.env` at process startup.

Use:

```bash
set -a
source .env
set +a
```

Then run CLI commands in the same shell.

## Safe Defaults

- `http.fetch` defaults to deny-all unless allowlist is provided.
- `fs` and `shell.exec` are constrained by `fs_root_path`.
- Tool calls are schema-validated before and after execution.
