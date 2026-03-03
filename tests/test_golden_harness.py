from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


class GoldenHarnessTests(unittest.TestCase):
    def test_golden_trace_validation(self):
        repo_root = Path(__file__).resolve().parents[1]
        proc = subprocess.run(
            [sys.executable, "scripts/validate_golden_traces.py"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("Golden trace validation passed", proc.stdout)


if __name__ == "__main__":
    unittest.main()
