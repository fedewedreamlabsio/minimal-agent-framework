from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .contracts import AgentState, JsonDict


class JsonlRunStore:
    def __init__(self, base_dir: str) -> None:
        self.base_path = Path(base_dir)

    def begin_run(self, run_id: str, metadata: JsonDict) -> None:
        run_dir = self._run_dir(run_id)
        run_dir.mkdir(parents=True, exist_ok=True)
        self._metadata_path(run_id).write_text(
            json.dumps(metadata, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def append_event(self, run_id: str, event: JsonDict) -> None:
        run_dir = self._run_dir(run_id)
        run_dir.mkdir(parents=True, exist_ok=True)
        with self._trace_path(run_id).open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, sort_keys=True))
            fh.write("\n")

    def save_state(self, run_id: str, state: AgentState, *, phase: str) -> None:
        run_dir = self._run_dir(run_id)
        run_dir.mkdir(parents=True, exist_ok=True)
        path = run_dir / f"state.{phase}.json"
        path.write_text(json.dumps(state.as_dict(), indent=2, sort_keys=True), encoding="utf-8")

    def finish_run(self, run_id: str, result: JsonDict) -> None:
        metadata = self.load_metadata(run_id)
        merged = dict(metadata)
        merged.update(result)
        self._metadata_path(run_id).write_text(
            json.dumps(merged, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def load_trace(self, run_id: str) -> list[JsonDict]:
        path = self._trace_path(run_id)
        if not path.exists():
            return []

        events: list[JsonDict] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            decoded = json.loads(line)
            if isinstance(decoded, dict):
                events.append(decoded)
        return events

    def load_state(self, run_id: str, *, phase: str = "final") -> JsonDict:
        path = self._run_dir(run_id) / f"state.{phase}.json"
        if not path.exists():
            return {}
        decoded = json.loads(path.read_text(encoding="utf-8"))
        return decoded if isinstance(decoded, dict) else {}

    def load_metadata(self, run_id: str) -> JsonDict:
        path = self._metadata_path(run_id)
        if not path.exists():
            return {}
        decoded = json.loads(path.read_text(encoding="utf-8"))
        return decoded if isinstance(decoded, dict) else {}

    def list_runs(self) -> list[str]:
        if not self.base_path.exists():
            return []
        return sorted([item.name for item in self.base_path.iterdir() if item.is_dir()])

    def _run_dir(self, run_id: str) -> Path:
        return self.base_path / run_id

    def _trace_path(self, run_id: str) -> Path:
        return self._run_dir(run_id) / "trace.jsonl"

    def _metadata_path(self, run_id: str) -> Path:
        return self._run_dir(run_id) / "metadata.json"


def extract_tool_results(trace: list[JsonDict]) -> list[JsonDict]:
    results: list[JsonDict] = []
    for event in trace:
        if event.get("type") != "tool_result":
            continue
        payload = event.get("payload", {})
        if isinstance(payload, dict):
            results.append(payload)
    return results


def extract_model_actions(trace: list[JsonDict]) -> list[JsonDict]:
    actions: list[JsonDict] = []
    for event in trace:
        if event.get("type") != "model_output":
            continue
        payload = event.get("payload", {})
        if not isinstance(payload, dict):
            continue
        action = payload.get("action")
        if isinstance(action, dict):
            actions.append(action)
    return actions
