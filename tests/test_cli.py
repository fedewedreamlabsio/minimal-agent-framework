from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


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


if __name__ == "__main__":
    unittest.main()
