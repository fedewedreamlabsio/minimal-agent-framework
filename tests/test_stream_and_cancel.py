from __future__ import annotations

import tempfile
import unittest

from maf import Action, AgentRuntime, JsonlRunStore, ModelResult, RuntimeConfig, ToolSpec


class ScriptedAdapter:
    def __init__(self, actions):
        self._actions = list(actions)

    def complete(self, **_kwargs):
        return ModelResult(action=self._actions.pop(0))


class CancelAdapter:
    def complete(self, **_kwargs):
        raise KeyboardInterrupt


class StreamAndCancelTests(unittest.TestCase):
    def test_streaming_emits_ordered_events(self):
        events = []

        def tool_handler(_payload, _state):
            return {"ok": True}

        tool = ToolSpec(
            name="noop",
            description="no op",
            input_schema={"type": "object", "additionalProperties": False},
            output_schema={
                "type": "object",
                "required": ["ok"],
                "properties": {"ok": {"type": "boolean"}},
                "additionalProperties": False,
            },
            timeout_seconds=1.0,
            handler=tool_handler,
        )

        runtime = AgentRuntime(
            config=RuntimeConfig(max_steps=4, max_run_seconds=2.0),
            llm_adapter=ScriptedAdapter(
                [
                    Action(type="tool_call", tool_name="noop", tool_input={}),
                    Action(type="final", final_output="done"),
                ]
            ),
            tools=[tool],
        )

        runtime.run("stream", event_handler=lambda e: events.append(e["type"]))

        self.assertEqual(
            events,
            [
                "run_started",
                "model_called",
                "model_output",
                "tool_called",
                "tool_result",
                "model_called",
                "model_output",
                "run_finished",
            ],
        )

    def test_cancellation_persists_partial_trace(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = JsonlRunStore(tmp)
            runtime = AgentRuntime(
                config=RuntimeConfig(trace_dir=tmp, max_steps=5, max_run_seconds=5.0),
                llm_adapter=CancelAdapter(),
                store=store,
            )

            result = runtime.run("cancel me")
            self.assertEqual(result.halt_reason, "cancelled")

            events = store.load_trace(result.run_id)
            self.assertGreaterEqual(len(events), 3)
            self.assertEqual(events[-1]["type"], "run_finished")
            self.assertEqual(events[-1]["payload"]["halt_reason"], "cancelled")


if __name__ == "__main__":
    unittest.main()
