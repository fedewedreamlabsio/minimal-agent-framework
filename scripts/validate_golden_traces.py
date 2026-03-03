#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from maf import Action, AgentRuntime, AgentState, MockAdapter, RuntimeConfig, ToolSpec


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate deterministic golden traces")
    parser.add_argument("--fixtures-dir", default="tests/golden", help="Directory for golden trace fixtures")
    parser.add_argument("--update", action="store_true", help="Regenerate fixture files")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    fixtures_dir = Path(args.fixtures_dir)
    fixtures_dir.mkdir(parents=True, exist_ok=True)

    actual = run_scenarios()

    if args.update:
        for name, trace in actual.items():
            (fixtures_dir / f"{name}.json").write_text(
                json.dumps(trace, indent=2, sort_keys=True),
                encoding="utf-8",
            )
        print(f"Updated {len(actual)} golden traces in {fixtures_dir}")
        return 0

    failures: list[str] = []
    for name, trace in actual.items():
        path = fixtures_dir / f"{name}.json"
        if not path.exists():
            failures.append(f"missing fixture: {path}")
            continue

        expected = json.loads(path.read_text(encoding="utf-8"))
        if expected != trace:
            failures.append(f"mismatch: {name}")

    if failures:
        print("Golden trace validation failed:")
        for failure in failures:
            print(f"- {failure}")
        print("Run with --update to refresh fixtures if the changes are intentional.")
        return 1

    print(f"Golden trace validation passed ({len(actual)} scenarios)")
    return 0


def run_scenarios() -> dict[str, list[dict[str, object]]]:
    return {
        "final_only": normalize_trace(run_final_only()),
        "tool_success": normalize_trace(run_tool_success()),
        "tool_timeout": normalize_trace(run_tool_timeout()),
    }


def run_final_only() -> list[dict[str, object]]:
    with tempfile.TemporaryDirectory() as tmp:
        runtime = AgentRuntime(
            config=RuntimeConfig(trace_dir=tmp, max_steps=4, max_run_seconds=3.0),
            llm_adapter=MockAdapter([Action(type="final", final_output="done")]),
        )
        state = AgentState(thread_id="golden-final-only")
        result = runtime.run("scenario:final_only", state=state)
    return result.trace


def run_tool_success() -> list[dict[str, object]]:
    def handler(_payload, _state):
        return {"ok": True, "value": "pong"}

    tool = ToolSpec(
        name="ping",
        description="return pong",
        input_schema={"type": "object", "additionalProperties": False},
        output_schema={
            "type": "object",
            "required": ["ok", "value"],
            "properties": {
                "ok": {"type": "boolean"},
                "value": {"type": "string"},
            },
            "additionalProperties": False,
        },
        timeout_seconds=1.0,
        handler=handler,
    )

    with tempfile.TemporaryDirectory() as tmp:
        runtime = AgentRuntime(
            config=RuntimeConfig(trace_dir=tmp, max_steps=4, max_run_seconds=3.0),
            llm_adapter=MockAdapter(
                [
                    Action(type="tool_call", tool_name="ping", tool_input={}),
                    Action(type="final", final_output="done"),
                ]
            ),
            tools=[tool],
        )
        state = AgentState(thread_id="golden-tool-success")
        result = runtime.run("scenario:tool_success", state=state)
    return result.trace


def run_tool_timeout() -> list[dict[str, object]]:
    def slow_handler(_payload, _state):
        time.sleep(0.2)
        return {"ok": True}

    tool = ToolSpec(
        name="slow",
        description="slow tool",
        input_schema={"type": "object", "additionalProperties": False},
        output_schema={
            "type": "object",
            "required": ["ok"],
            "properties": {
                "ok": {"type": "boolean"},
            },
            "additionalProperties": False,
        },
        timeout_seconds=0.05,
        handler=slow_handler,
    )

    with tempfile.TemporaryDirectory() as tmp:
        runtime = AgentRuntime(
            config=RuntimeConfig(trace_dir=tmp, max_steps=4, max_run_seconds=3.0),
            llm_adapter=MockAdapter(
                [
                    Action(type="tool_call", tool_name="slow", tool_input={}),
                    Action(type="final", final_output="never"),
                ]
            ),
            tools=[tool],
        )
        state = AgentState(thread_id="golden-tool-timeout")
        result = runtime.run("scenario:tool_timeout", state=state)
    return result.trace


def normalize_trace(trace: list[dict[str, object]]) -> list[dict[str, object]]:
    normalized: list[dict[str, object]] = []
    for event in trace:
        normalized.append(
            {
                "type": event.get("type"),
                "payload": event.get("payload", {}),
            }
        )
    return normalized


if __name__ == "__main__":
    raise SystemExit(main())
