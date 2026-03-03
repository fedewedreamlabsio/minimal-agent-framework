from __future__ import annotations

import tempfile
import unittest

from maf import Action, AgentRuntime, MockAdapter, ReplayAdapter, RuntimeConfig, ToolSpec
from maf.store import extract_tool_results


class ReplayTests(unittest.TestCase):
    def test_replay_uses_recorded_tool_results(self):
        calls = {"count": 0}

        def handler(_payload, _state):
            calls["count"] += 1
            return {"ok": True, "value": calls["count"]}

        counter_tool = ToolSpec(
            name="counter",
            description="increment counter",
            input_schema={"type": "object", "additionalProperties": False},
            output_schema={
                "type": "object",
                "required": ["ok", "value"],
                "properties": {
                    "ok": {"type": "boolean"},
                    "value": {"type": "integer"},
                },
                "additionalProperties": False,
            },
            timeout_seconds=1.0,
            handler=handler,
        )

        actions = [
            Action(type="tool_call", tool_name="counter", tool_input={}),
            Action(type="final", final_output="done"),
        ]

        with tempfile.TemporaryDirectory() as tmp:
            config = RuntimeConfig(trace_dir=tmp, max_steps=4, max_run_seconds=2.0)

            first_runtime = AgentRuntime(
                config=config,
                llm_adapter=MockAdapter(scripted_actions=list(actions)),
                tools=[counter_tool],
            )
            first = first_runtime.run("count once")
            self.assertEqual(calls["count"], 1)

            replay_runtime = AgentRuntime(
                config=config,
                llm_adapter=ReplayAdapter.from_trace(first.trace),
                tools=[counter_tool],
            )
            replay = replay_runtime.run(
                "count once",
                replay_tool_results=extract_tool_results(first.trace),
            )

            self.assertEqual(replay.final_output, "done")
            self.assertEqual(calls["count"], 1, "tool should not execute during replay")
            replay_tool_events = [e for e in replay.trace if e["type"] == "tool_result"]
            self.assertTrue(replay_tool_events[-1]["payload"]["replayed"])


if __name__ == "__main__":
    unittest.main()
