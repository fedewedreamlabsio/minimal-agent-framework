from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from maf import Action, AgentRuntime, JsonlRunStore, RuntimeConfig
from maf.llm import MockAdapter


class TraceStoreTests(unittest.TestCase):
    def test_trace_and_state_are_persisted(self):
        with tempfile.TemporaryDirectory() as tmp:
            trace_dir = str(Path(tmp) / "runs")
            config = RuntimeConfig(trace_dir=trace_dir, max_steps=3, max_run_seconds=2.0)
            store = JsonlRunStore(trace_dir)
            runtime = AgentRuntime(
                config=config,
                llm_adapter=MockAdapter([Action(type="final", final_output="ok")]),
                store=store,
            )

            result = runtime.run("hello")
            run_dir = Path(trace_dir) / result.run_id

            self.assertTrue((run_dir / "trace.jsonl").exists())
            self.assertTrue((run_dir / "state.initial.json").exists())
            self.assertTrue((run_dir / "state.final.json").exists())
            self.assertTrue((run_dir / "metadata.json").exists())

            events = store.load_trace(result.run_id)
            self.assertGreaterEqual(len(events), 3)
            self.assertEqual(events[0]["type"], "run_started")
            self.assertEqual(events[-1]["type"], "run_finished")

            final_state = store.load_state(result.run_id)
            self.assertEqual(final_state["messages"][-1]["role"], "assistant")

            metadata = store.load_metadata(result.run_id)
            self.assertEqual(metadata["status"], "completed")


if __name__ == "__main__":
    unittest.main()
