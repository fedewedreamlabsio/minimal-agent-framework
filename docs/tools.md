# Tool Contracts

Built-in power tools are created by `build_power_tools()` in `maf/power_tools.py`.

## `shell.exec`

Purpose:
- Execute local shell command.

Input:
- `cmd` string (required)
- `cwd` string (optional, relative/absolute path constrained to `fs_root_path`)
- `timeout_seconds` number (optional)

Output:
- `success` boolean
- `timed_out` boolean
- `exit_code` integer|null
- `stdout` string
- `stderr` string

## `fs`

Purpose:
- Read, write, or list files.

Input:
- `op` enum: `read|write|list`
- `path` string
- `content` string (write only)
- `encoding` string (optional)
- `create_dirs` boolean (write only)

Output includes:
- `ok`, `op`, `path`
- `content` for read
- `bytes_written` for write
- `entries[]` for list

Safety:
- Paths are resolved and must remain under `fs_root_path`.

## `http.fetch`

Purpose:
- HTTP GET/POST-like fetch with strict allowlist.

Input:
- `url` string (required)
- `method` string (optional, defaults to `GET`)
- `headers` object (optional)
- `body` string|null (optional)
- `timeout_seconds` number (optional)

Output:
- `ok` boolean (2xx)
- `status` integer
- `headers` object
- `body` string

Safety:
- Deny-by-default when allowlist is empty.
- URL must start with one of allowed prefixes.

## `kv.get` and `kv.set`

Purpose:
- Simple file-backed key-value persistence.

`kv.get` input:
- `key` string

`kv.get` output:
- `ok`, `key`, `found`, `value`

`kv.set` input:
- `key` string
- `value` any JSON-compatible value

`kv.set` output:
- `ok`, `key`, `value`

Storage:
- Uses `RuntimeConfig.kv_store_path`.

## Validation Pipeline

For every tool call:
1. Validate input payload against tool input schema.
2. Execute tool (or use replayed output).
3. Validate output against tool output schema.
4. Emit `tool_result` event.

Validation errors are emitted as `error` events and halt the run.
