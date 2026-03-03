from __future__ import annotations

import time
import unittest

from maf import Action, AgentRuntime, ModelResult, RuntimeConfig


class ScriptedAdapter:
    def __init__(self, actions):
        self._actions = list(actions)

    def complete(self, **_kwargs):
        if self._actions:
            action = self._actions.pop(0)
        else:
            action = Action(type="continue", internal_note="still working")
        return ModelResult(action=action)


class SlowAdapter:
    def complete(self, **_kwargs):
        time.sleep(0.03)
        return ModelResult(action=Action(type="continue", internal_note="sleep"))


class RuntimeLoopTests(unittest.TestCase):
    def test_final_action_completes_run(self):
        runtime = AgentRuntime(
            config=RuntimeConfig(max_steps=4, max_run_seconds=2.0),
            llm_adapter=ScriptedAdapter([Action(type="final", final_output="done")]),
        )

        result = runtime.run("hello")

        self.assertEqual(result.final_output, "done")
        self.assertIsNone(result.halt_reason)
        self.assertEqual(result.trace[-1]["type"], "run_finished")
        self.assertEqual(result.trace[-1]["payload"]["status"], "completed")

    def test_max_steps_halts_run(self):
        runtime = AgentRuntime(
            config=RuntimeConfig(max_steps=2, max_run_seconds=2.0),
            llm_adapter=ScriptedAdapter(
                [
                    Action(type="continue", internal_note="1"),
                    Action(type="continue", internal_note="2"),
                    Action(type="continue", internal_note="3"),
                ]
            ),
        )

        result = runtime.run("loop")

        self.assertEqual(result.halt_reason, "max_steps")
        self.assertEqual(result.trace[-1]["payload"]["status"], "halted")

    def test_runtime_budget_halts_run(self):
        runtime = AgentRuntime(
            config=RuntimeConfig(max_steps=5, max_run_seconds=0.02),
            llm_adapter=SlowAdapter(),
        )

        result = runtime.run("slow")

        self.assertEqual(result.halt_reason, "max_runtime_seconds")


if __name__ == "__main__":
    unittest.main()
