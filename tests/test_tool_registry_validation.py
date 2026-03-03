from __future__ import annotations

import unittest

from maf import Action, AgentRuntime, ModelResult, RuntimeConfig, ToolSpec
from maf.tooling import ToolRegistry


class ScriptedAdapter:
    def __init__(self, actions):
        self._actions = list(actions)

    def complete(self, **_kwargs):
        action = self._actions.pop(0)
        return ModelResult(action=action)


def make_echo_tool() -> ToolSpec:
    def handler(payload, _state):
        return {"ok": True, "echo": payload["text"]}

    return ToolSpec(
        name="echo",
        description="echo text",
        input_schema={
            "type": "object",
            "required": ["text"],
            "properties": {
                "text": {"type": "string"},
            },
            "additionalProperties": False,
        },
        output_schema={
            "type": "object",
            "required": ["ok", "echo"],
            "properties": {
                "ok": {"type": "boolean"},
                "echo": {"type": "string"},
            },
            "additionalProperties": False,
        },
        timeout_seconds=1.0,
        handler=handler,
    )


class ToolValidationTests(unittest.TestCase):
    def test_duplicate_tool_registration_is_rejected(self):
        tool = make_echo_tool()
        registry = ToolRegistry([tool])
        with self.assertRaises(ValueError):
            registry.register(tool)

    def test_invalid_tool_input_halts_before_execution(self):
        runtime = AgentRuntime(
            config=RuntimeConfig(max_steps=3, max_run_seconds=2.0),
            llm_adapter=ScriptedAdapter(
                [
                    Action(type="tool_call", tool_name="echo", tool_input={}),
                    Action(type="final", final_output="never"),
                ]
            ),
            tools=[make_echo_tool()],
        )

        result = runtime.run("invalid")

        self.assertEqual(result.halt_reason, "tool_input_validation_failed")
        errors = [event for event in result.trace if event["type"] == "error"]
        self.assertTrue(errors)
        self.assertIn("validation_errors", errors[-1]["payload"])

    def test_valid_tool_input_executes(self):
        runtime = AgentRuntime(
            config=RuntimeConfig(max_steps=4, max_run_seconds=2.0),
            llm_adapter=ScriptedAdapter(
                [
                    Action(type="tool_call", tool_name="echo", tool_input={"text": "hello"}),
                    Action(type="final", final_output="done"),
                ]
            ),
            tools=[make_echo_tool()],
        )

        result = runtime.run("valid")

        self.assertIsNone(result.halt_reason)
        tool_events = [event for event in result.trace if event["type"] == "tool_result"]
        self.assertEqual(tool_events[-1]["payload"]["output"]["echo"], "hello")


if __name__ == "__main__":
    unittest.main()
