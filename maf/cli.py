from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .contracts import RuntimeConfig
from .llm import MockAdapter, OpenAIChatAdapter, ReplayAdapter
from .power_tools import build_power_tools
from .runtime import AgentRuntime
from .store import JsonlRunStore, extract_tool_results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="maf", description="Minimal Agent Framework CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Execute an agent run")
    run.add_argument("--input", required=True, help="User input message")
    run.add_argument("--provider", default="mock", choices=["mock", "openai"], help="LLM provider")
    run.add_argument("--model", default="gpt-4.1-mini", help="Model identifier")
    run.add_argument("--trace-dir", default=".maf/runs", help="Run trace directory")
    run.add_argument("--max-steps", type=int, default=12)
    run.add_argument("--max-run-seconds", type=float, default=90.0)
    run.add_argument("--stream-events", action="store_true", help="Print structured events during run")
    run.add_argument("--disable-power-tools", action="store_true", help="Disable default power tools")

    trace = sub.add_parser("trace", help="Show persisted trace events")
    trace.add_argument("--run-id", required=True)
    trace.add_argument("--trace-dir", default=".maf/runs")

    replay = sub.add_parser("replay", help="Replay a previous run")
    replay.add_argument("--run-id", required=True)
    replay.add_argument("--trace-dir", default=".maf/runs")
    replay.add_argument("--input", help="Optional override for replay input")
    replay.add_argument("--stream-events", action="store_true")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "run":
        return _cmd_run(args)
    if args.command == "trace":
        return _cmd_trace(args)
    if args.command == "replay":
        return _cmd_replay(args)

    print(f"unsupported command: {args.command}", file=sys.stderr)
    return 1


def _cmd_run(args: argparse.Namespace) -> int:
    config = RuntimeConfig(
        provider=args.provider,
        model=args.model,
        max_steps=args.max_steps,
        max_run_seconds=args.max_run_seconds,
        trace_dir=args.trace_dir,
        http_allowlist=_parse_csv_allowlist("MAF_HTTP_ALLOWLIST"),
        fs_root_path=str(Path(".").resolve()),
        kv_store_path=str(Path(args.trace_dir) / "kv.json"),
    )

    adapter = _build_adapter(args.provider, args.model)
    tools = [] if args.disable_power_tools else build_power_tools(config)
    runtime = AgentRuntime(config=config, llm_adapter=adapter, tools=tools)

    event_handler = _print_event if args.stream_events else None
    result = runtime.run(args.input, event_handler=event_handler)

    print(f"run_id={result.run_id}")
    print(f"status={'completed' if result.halt_reason is None else 'halted'}")
    if result.halt_reason:
        print(f"halt_reason={result.halt_reason}")
    print(f"final_output={result.final_output}")
    return 0


def _cmd_trace(args: argparse.Namespace) -> int:
    store = JsonlRunStore(args.trace_dir)
    trace = store.load_trace(args.run_id)
    if not trace:
        print(f"no trace found for run_id={args.run_id}", file=sys.stderr)
        return 1

    for event in trace:
        ts = event.get("ts", "")
        event_type = event.get("type", "unknown")
        payload = event.get("payload", {})
        print(f"[{ts}] {event_type} {json.dumps(payload, sort_keys=True)}")
    return 0


def _cmd_replay(args: argparse.Namespace) -> int:
    store = JsonlRunStore(args.trace_dir)
    trace = store.load_trace(args.run_id)
    if not trace:
        print(f"no trace found for run_id={args.run_id}", file=sys.stderr)
        return 1

    metadata = store.load_metadata(args.run_id)
    input_text = args.input or str(metadata.get("input", ""))
    if not input_text:
        print("replay input is empty; pass --input explicitly", file=sys.stderr)
        return 1

    config = RuntimeConfig(
        provider="replay",
        model=str(metadata.get("model", "replay")),
        max_steps=int(metadata.get("max_steps", 12)),
        max_run_seconds=float(metadata.get("max_run_seconds", 90.0)),
        trace_dir=args.trace_dir,
        http_allowlist=_parse_csv_allowlist("MAF_HTTP_ALLOWLIST"),
        fs_root_path=str(Path(".").resolve()),
        kv_store_path=str(Path(args.trace_dir) / "kv.json"),
    )

    runtime = AgentRuntime(
        config=config,
        llm_adapter=ReplayAdapter.from_trace(trace),
        tools=build_power_tools(config),
    )

    event_handler = _print_event if args.stream_events else None
    replay_result = runtime.run(
        input_text,
        replay_tool_results=extract_tool_results(trace),
        event_handler=event_handler,
    )

    print(f"replay_of={args.run_id}")
    print(f"run_id={replay_result.run_id}")
    print(f"status={'completed' if replay_result.halt_reason is None else 'halted'}")
    if replay_result.halt_reason:
        print(f"halt_reason={replay_result.halt_reason}")
    print(f"final_output={replay_result.final_output}")
    return 0


def _build_adapter(provider: str, model: str):
    if provider == "mock":
        return MockAdapter()
    if provider == "openai":
        return OpenAIChatAdapter(model=model)
    raise ValueError(f"unsupported provider: {provider}")


def _print_event(event: dict[str, object]) -> None:
    print(json.dumps(event, sort_keys=True), flush=True)


def _parse_csv_allowlist(env_name: str) -> list[str]:
    raw = str(__import__("os").environ.get(env_name, "")).strip()
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


if __name__ == "__main__":
    raise SystemExit(main())
