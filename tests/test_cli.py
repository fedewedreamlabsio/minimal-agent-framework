from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from maf.cli import _resolve_model


class CliTests(unittest.TestCase):
    def test_run_trace_replay_flow(self):
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            trace_dir = str(Path(tmp) / "runs")

            run_cmd = [
                sys.executable,
                "-m",
                "maf.cli",
                "run",
                "--provider",
                "mock",
                "--input",
                "hello",
                "--trace-dir",
                trace_dir,
            ]
            run_proc = subprocess.run(run_cmd, cwd=repo_root, capture_output=True, text=True, check=True)
            self.assertIn("run_id=", run_proc.stdout)

            run_id = ""
            for line in run_proc.stdout.splitlines():
                if line.startswith("run_id="):
                    run_id = line.split("=", 1)[1].strip()
            self.assertTrue(run_id)

            trace_cmd = [
                sys.executable,
                "-m",
                "maf.cli",
                "trace",
                "--run-id",
                run_id,
                "--trace-dir",
                trace_dir,
            ]
            trace_proc = subprocess.run(trace_cmd, cwd=repo_root, capture_output=True, text=True, check=True)
            self.assertIn("run_started", trace_proc.stdout)
            self.assertIn("run_finished", trace_proc.stdout)

            replay_cmd = [
                sys.executable,
                "-m",
                "maf.cli",
                "replay",
                "--run-id",
                run_id,
                "--trace-dir",
                trace_dir,
            ]
            replay_proc = subprocess.run(replay_cmd, cwd=repo_root, capture_output=True, text=True, check=True)
            self.assertIn(f"replay_of={run_id}", replay_proc.stdout)
            self.assertIn("status=completed", replay_proc.stdout)

    def test_provider_default_model_resolution(self):
        self.assertEqual(_resolve_model("mock", None), "mock-model")
        self.assertEqual(_resolve_model("openai", None), "gpt-4.1-mini")
        self.assertEqual(_resolve_model("cerebras", None), "zai-glm-4.7")
        self.assertEqual(_resolve_model("cerebras", "custom-model"), "custom-model")

    def test_perf_command_reports_expected_metrics(self):
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            trace_dir = Path(tmp) / "runs"
            run_id = "run-perf-1"
            run_path = trace_dir / run_id
            run_path.mkdir(parents=True, exist_ok=True)

            events = [
                {
                    "run_id": run_id,
                    "ts": "2026-03-03T10:00:00+00:00",
                    "type": "run_started",
                    "payload": {},
                },
                {
                    "run_id": run_id,
                    "ts": "2026-03-03T10:00:01+00:00",
                    "type": "model_called",
                    "payload": {"step": 0},
                },
                {
                    "run_id": run_id,
                    "ts": "2026-03-03T10:00:03+00:00",
                    "type": "model_output",
                    "payload": {"step": 0, "usage": {"completion_tokens": 100, "prompt_tokens": 200, "total_tokens": 300}},
                },
                {
                    "run_id": run_id,
                    "ts": "2026-03-03T10:00:05+00:00",
                    "type": "run_finished",
                    "payload": {},
                },
            ]

            trace_file = run_path / "trace.jsonl"
            trace_file.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")

            proc = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "maf.cli",
                    "perf",
                    "--run-id",
                    run_id,
                    "--trace-dir",
                    str(trace_dir),
                ],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=True,
            )

            lines = {}
            for line in proc.stdout.splitlines():
                if "=" in line:
                    k, v = line.split("=", 1)
                    lines[k] = v

            self.assertEqual(lines["model_calls"], "1")
            self.assertEqual(lines["completion_tokens"], "100")
            self.assertEqual(lines["prompt_tokens"], "200")
            self.assertEqual(lines["total_tokens"], "300")
            self.assertEqual(lines["model_seconds"], "2.000000")
            self.assertEqual(lines["wall_seconds"], "5.000000")
            self.assertEqual(lines["completion_tps_model_time"], "50.00")
            self.assertEqual(lines["completion_tps_wall_time"], "20.00")


if __name__ == "__main__":
    unittest.main()
