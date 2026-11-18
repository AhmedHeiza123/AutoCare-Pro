"""Credential validation must happen before any database access or imports."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "app" / "sample_data.py"


class DemoCredentialTests(unittest.TestCase):
    def run_demo(self, password=None):
        env = os.environ.copy()
        env.pop("AUTOCARE_DEMO_PASSWORD", None)
        if password is not None:
            env["AUTOCARE_DEMO_PASSWORD"] = password
        # Isolate imports so a broken validation cannot connect to a real database.
        with tempfile.TemporaryDirectory() as folder:
            script = Path(folder) / "sample_data.py"
            script.write_bytes(SCRIPT.read_bytes())
            return subprocess.run(
                [sys.executable, str(script), "--database", "autocare_demo"],
                env=env, cwd=folder, text=True, capture_output=True, timeout=15,
            )

    def test_missing_password_is_rejected_before_database_access(self):
        result = self.run_demo()
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("AUTOCARE_DEMO_PASSWORD", result.stdout)
        self.assertNotIn("Traceback", result.stderr)

    def test_short_password_is_rejected_without_disclosure(self):
        private_value = "short!"
        result = self.run_demo(private_value)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertNotIn(private_value, result.stdout + result.stderr)

    def test_whitespace_password_is_rejected_without_database_access(self):
        result = self.run_demo(" " * 16)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
