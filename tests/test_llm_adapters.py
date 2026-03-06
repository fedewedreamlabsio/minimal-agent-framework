from __future__ import annotations

import os
import unittest

from maf import Action
from maf.contracts import AgentState, RuntimeConfig
from maf.llm import (
    AdapterError,
    CerebrasChatAdapter,
    MockAdapter,
    OpenAIChatAdapter,
    action_from_dict,
    parse_action_json,
)


class ParserTests(unittest.TestCase):
    def test_parse_plain_json(self):
        action = parse_action_json('{"type":"final","final_output":"ok"}')
        self.assertEqual(action.type, "final")
        self.assertEqual(action.final_output, "ok")

    def test_parse_fenced_json(self):
        action = parse_action_json("```json\n{\"type\":\"continue\"}\n```")
        self.assertEqual(action.type, "continue")

    def test_parse_recovers_malformed_json(self):
        malformed = 'LLM output:\n{"type":"final","final_output":"line1\nline2","internal_note":"draft",'

        with self.assertLogs("maf.llm", level="WARNING") as logs:
            action = parse_action_json(malformed)

        self.assertEqual(action.type, "final")
        self.assertEqual(action.final_output, "line1\nline2")
        self.assertEqual(action.internal_note, "draft")
        self.assertIn("Recovered malformed action JSON", logs.output[0])

    def test_action_from_dict_infers_tool_call_when_type_missing(self):
        action = action_from_dict({"tool_name": "fs", "tool_input": {"op": "write"}})
        self.assertEqual(action.type, "tool_call")
        self.assertEqual(action.tool_name, "fs")

    def test_action_from_dict_infers_final_when_type_missing(self):
        action = action_from_dict({"final_output": "done"})
        self.assertEqual(action.type, "final")
        self.assertEqual(action.final_output, "done")


class MockAdapterTests(unittest.TestCase):
    def test_scripted_actions_are_deterministic(self):
        adapter = MockAdapter(scripted_actions=[Action(type="continue"), Action(type="final", final_output="done")])
        state = AgentState(thread_id="t1", messages=[{"role": "user", "content": "hello"}])

        first = adapter.complete(run_id="r", step_index=0, state=state, tools=[], config=RuntimeConfig())
        second = adapter.complete(run_id="r", step_index=1, state=state, tools=[], config=RuntimeConfig())

        self.assertEqual(first.action.type, "continue")
        self.assertEqual(second.action.type, "final")
        self.assertEqual(second.action.final_output, "done")

    def test_default_fallback_echoes_user_input(self):
        adapter = MockAdapter()
        state = AgentState(thread_id="t2", messages=[{"role": "user", "content": "ping"}])

        result = adapter.complete(run_id="r", step_index=0, state=state, tools=[], config=RuntimeConfig())

        self.assertEqual(result.action.type, "final")
        self.assertEqual(result.action.final_output, "Echo: ping")


class OpenAIAdapterTests(unittest.TestCase):
    def test_openai_adapter_requires_key(self):
        old = os.environ.pop("OPENAI_API_KEY", None)
        self.addCleanup(lambda: os.environ.__setitem__("OPENAI_API_KEY", old) if old is not None else None)

        adapter = OpenAIChatAdapter()
        state = AgentState(thread_id="t3", messages=[{"role": "user", "content": "hello"}])

        with self.assertRaises(AdapterError):
            adapter.complete(run_id="r", step_index=0, state=state, tools=[], config=RuntimeConfig())


class CerebrasAdapterTests(unittest.TestCase):
    def test_cerebras_adapter_requires_key(self):
        old = os.environ.pop("CEREBRAS_API_KEY", None)
        self.addCleanup(lambda: os.environ.__setitem__("CEREBRAS_API_KEY", old) if old is not None else None)

        adapter = CerebrasChatAdapter()
        state = AgentState(thread_id="t4", messages=[{"role": "user", "content": "hello"}])

        with self.assertRaises(AdapterError):
            adapter.complete(run_id="r", step_index=0, state=state, tools=[], config=RuntimeConfig())


if __name__ == "__main__":
    unittest.main()
