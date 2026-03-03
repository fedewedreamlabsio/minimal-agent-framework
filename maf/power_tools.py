from __future__ import annotations

import json
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from .contracts import AgentState, RuntimeConfig, ToolSpec


def build_power_tools(config: RuntimeConfig) -> list[ToolSpec]:
    return [
        _make_shell_exec_tool(config),
        _make_fs_tool(config),
        _make_http_fetch_tool(config),
        _make_kv_get_tool(config),
        _make_kv_set_tool(config),
    ]


def _make_shell_exec_tool(config: RuntimeConfig) -> ToolSpec:
    def handler(payload: dict[str, Any], _state: AgentState) -> dict[str, Any]:
        cmd = str(payload["cmd"])
        timeout = float(payload.get("timeout_seconds", config.default_tool_timeout_seconds))
        cwd_raw = payload.get("cwd", ".")
        cwd = _resolve_within_root(cwd_raw, config.fs_root_path)

        try:
            completed = subprocess.run(
                cmd,
                shell=True,
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            return {
                "success": completed.returncode == 0,
                "timed_out": False,
                "exit_code": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            }
        except subprocess.TimeoutExpired as exc:
            return {
                "success": False,
                "timed_out": True,
                "exit_code": None,
                "stdout": exc.stdout.decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or ""),
                "stderr": exc.stderr.decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or ""),
            }

    return ToolSpec(
        name="shell.exec",
        description="Execute a local shell command within the configured filesystem root.",
        input_schema={
            "type": "object",
            "required": ["cmd"],
            "properties": {
                "cmd": {"type": "string"},
                "cwd": {"type": "string"},
                "timeout_seconds": {"type": "number"},
            },
            "additionalProperties": False,
        },
        output_schema={
            "type": "object",
            "required": ["success", "timed_out", "exit_code", "stdout", "stderr"],
            "properties": {
                "success": {"type": "boolean"},
                "timed_out": {"type": "boolean"},
                "exit_code": {"type": ["integer", "null"]},
                "stdout": {"type": "string"},
                "stderr": {"type": "string"},
            },
            "additionalProperties": False,
        },
        timeout_seconds=max(config.default_tool_timeout_seconds, 0.1),
        handler=handler,
    )


def _make_fs_tool(config: RuntimeConfig) -> ToolSpec:
    root = Path(config.fs_root_path).resolve()

    def handler(payload: dict[str, Any], _state: AgentState) -> dict[str, Any]:
        op = payload["op"]
        path = payload["path"]
        target = _resolve_within_root(path, str(root))

        if op == "read":
            content = target.read_text(encoding=str(payload.get("encoding", "utf-8")))
            return {"ok": True, "op": "read", "path": str(target.relative_to(root)), "content": content}

        if op == "write":
            content = payload.get("content", "")
            if not isinstance(content, str):
                raise ValueError("fs write content must be a string")
            if payload.get("create_dirs", True):
                target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding=str(payload.get("encoding", "utf-8")))
            return {
                "ok": True,
                "op": "write",
                "path": str(target.relative_to(root)),
                "bytes_written": len(content.encode(str(payload.get("encoding", "utf-8")))),
            }

        if op == "list":
            if not target.exists():
                raise FileNotFoundError(f"path does not exist: {target}")
            if not target.is_dir():
                raise NotADirectoryError(f"path is not a directory: {target}")

            entries = []
            for child in sorted(target.iterdir(), key=lambda p: p.name):
                rel = child.relative_to(root)
                entries.append(
                    {
                        "name": child.name,
                        "path": str(rel),
                        "is_dir": child.is_dir(),
                    }
                )
            return {"ok": True, "op": "list", "path": str(target.relative_to(root)), "entries": entries}

        raise ValueError(f"unsupported fs op: {op}")

    return ToolSpec(
        name="fs",
        description="Read, write, or list files within the configured filesystem root.",
        input_schema={
            "type": "object",
            "required": ["op", "path"],
            "properties": {
                "op": {"enum": ["read", "write", "list"]},
                "path": {"type": "string"},
                "content": {"type": "string"},
                "encoding": {"type": "string"},
                "create_dirs": {"type": "boolean"},
            },
            "additionalProperties": False,
        },
        output_schema={
            "type": "object",
            "required": ["ok", "op", "path"],
            "properties": {
                "ok": {"type": "boolean"},
                "op": {"enum": ["read", "write", "list"]},
                "path": {"type": "string"},
                "content": {"type": "string"},
                "bytes_written": {"type": "integer"},
                "entries": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["name", "path", "is_dir"],
                        "properties": {
                            "name": {"type": "string"},
                            "path": {"type": "string"},
                            "is_dir": {"type": "boolean"},
                        },
                        "additionalProperties": False,
                    },
                },
            },
            "additionalProperties": False,
        },
        timeout_seconds=max(config.default_tool_timeout_seconds, 0.1),
        handler=handler,
    )


def _make_http_fetch_tool(config: RuntimeConfig) -> ToolSpec:
    allowlist = list(config.http_allowlist)

    def handler(payload: dict[str, Any], _state: AgentState) -> dict[str, Any]:
        url = str(payload["url"])
        method = str(payload.get("method", "GET")).upper()
        headers = payload.get("headers") or {}
        body = payload.get("body")
        timeout = float(payload.get("timeout_seconds", config.default_tool_timeout_seconds))

        if not _is_url_allowed(url, allowlist):
            raise PermissionError("url is not allowed by MAF_HTTP_ALLOWLIST")

        if not isinstance(headers, dict):
            raise ValueError("headers must be an object")

        encoded_body = None
        if body is not None:
            encoded_body = str(body).encode("utf-8")

        request = urllib.request.Request(
            url,
            data=encoded_body,
            headers={str(k): str(v) for k, v in headers.items()},
            method=method,
        )

        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                data = response.read().decode("utf-8", errors="replace")
                status = int(response.status)
                response_headers = dict(response.headers.items())
        except urllib.error.HTTPError as exc:
            status = int(exc.code)
            data = exc.read().decode("utf-8", errors="replace")
            response_headers = dict(exc.headers.items()) if exc.headers is not None else {}

        return {
            "ok": 200 <= status < 300,
            "status": status,
            "headers": response_headers,
            "body": data,
        }

    return ToolSpec(
        name="http.fetch",
        description="Fetch a URL via HTTP(S) with strict allowlist validation.",
        input_schema={
            "type": "object",
            "required": ["url"],
            "properties": {
                "url": {"type": "string"},
                "method": {"type": "string"},
                "headers": {"type": "object"},
                "body": {"type": ["string", "null"]},
                "timeout_seconds": {"type": "number"},
            },
            "additionalProperties": False,
        },
        output_schema={
            "type": "object",
            "required": ["ok", "status", "headers", "body"],
            "properties": {
                "ok": {"type": "boolean"},
                "status": {"type": "integer"},
                "headers": {"type": "object"},
                "body": {"type": "string"},
            },
            "additionalProperties": False,
        },
        timeout_seconds=max(config.default_tool_timeout_seconds, 0.1),
        handler=handler,
    )


def _make_kv_get_tool(config: RuntimeConfig) -> ToolSpec:
    def handler(payload: dict[str, Any], _state: AgentState) -> dict[str, Any]:
        key = str(payload["key"])
        kv = _load_kv(config.kv_store_path)
        found = key in kv
        return {"ok": True, "key": key, "found": found, "value": kv.get(key)}

    return ToolSpec(
        name="kv.get",
        description="Read a value from the file-backed KV store.",
        input_schema={
            "type": "object",
            "required": ["key"],
            "properties": {
                "key": {"type": "string"},
            },
            "additionalProperties": False,
        },
        output_schema={
            "type": "object",
            "required": ["ok", "key", "found", "value"],
            "properties": {
                "ok": {"type": "boolean"},
                "key": {"type": "string"},
                "found": {"type": "boolean"},
                "value": {},
            },
            "additionalProperties": False,
        },
        timeout_seconds=max(config.default_tool_timeout_seconds, 0.1),
        handler=handler,
    )


def _make_kv_set_tool(config: RuntimeConfig) -> ToolSpec:
    def handler(payload: dict[str, Any], _state: AgentState) -> dict[str, Any]:
        key = str(payload["key"])
        value = payload.get("value")
        kv = _load_kv(config.kv_store_path)
        kv[key] = value
        _save_kv(config.kv_store_path, kv)
        return {"ok": True, "key": key, "value": value}

    return ToolSpec(
        name="kv.set",
        description="Write a value to the file-backed KV store.",
        input_schema={
            "type": "object",
            "required": ["key", "value"],
            "properties": {
                "key": {"type": "string"},
                "value": {},
            },
            "additionalProperties": False,
        },
        output_schema={
            "type": "object",
            "required": ["ok", "key", "value"],
            "properties": {
                "ok": {"type": "boolean"},
                "key": {"type": "string"},
                "value": {},
            },
            "additionalProperties": False,
        },
        timeout_seconds=max(config.default_tool_timeout_seconds, 0.1),
        handler=handler,
    )


def _resolve_within_root(path_like: str, root_path: str) -> Path:
    root = Path(root_path).resolve()
    candidate = (root / path_like).resolve() if not Path(path_like).is_absolute() else Path(path_like).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise PermissionError(f"path escapes configured fs root: {path_like}") from exc
    return candidate


def _is_url_allowed(url: str, allowlist: list[str]) -> bool:
    if not allowlist:
        return False
    return any(url.startswith(prefix) for prefix in allowlist)


def _load_kv(path_like: str) -> dict[str, Any]:
    path = Path(path_like)
    if not path.exists():
        return {}
    raw = path.read_text(encoding="utf-8")
    decoded = json.loads(raw)
    return decoded if isinstance(decoded, dict) else {}


def _save_kv(path_like: str, data: dict[str, Any]) -> None:
    path = Path(path_like)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
