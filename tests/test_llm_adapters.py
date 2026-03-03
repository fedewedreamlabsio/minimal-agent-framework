from __future__ import annotations

import os
import unittest

from maf import Action
from maf.contracts import AgentState, RuntimeConfig
from maf.llm import AdapterError, MockAdapter, OpenAIChatAdapter, parse_action_json


class ParserTests(unittest.TestCase):
    def test_parse_plain_json(self):
        action = parse_action_json('{"type":"final","final_output":"ok"}')
        self.assertEqual(action.type, "final")
        self.assertEqual(action.final_output, "ok")

    def test_parse_fenced_json(self):
        action = parse_action_json("```json\n{\"type\":\"continue\"}\n```")
        self.assertEqual(action.type, "continue")


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


if __name__ == "__main__":
    unittest.main()
