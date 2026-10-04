from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from snake_lang import __version__


class StandaloneExecutableTests(unittest.TestCase):
    def test_standalone_executable_runs_without_python_on_path(self) -> None:
        executable_value = os.environ.get("SNAKE_TEST_EXE")
        if not executable_value:
            self.skipTest("Set SNAKE_TEST_EXE to run packaged executable integration tests.")
        executable = Path(executable_value).resolve()
        if not executable.is_file():
            self.fail(f"SNAKE_TEST_EXE does not exist: {executable}")

        environment = os.environ.copy()
        for key in list(environment):
            if key.upper().startswith("PYTHON"):
                del environment[key]
        environment["PATH"] = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32")

        with tempfile.TemporaryDirectory(prefix="snake-exe-test-") as temporary:
            directory = Path(temporary)
            program = directory / "hello.snake"
            program.write_text("show math.sqrt(49)\n", encoding="utf-8")

            version = subprocess.run([str(executable), "--version"], cwd=directory,
                                     env=environment, capture_output=True, text=True, timeout=60)
            self.assertEqual(version.returncode, 0, version.stderr)
            self.assertIn(f"Snake {__version__}", version.stdout)

            run = subprocess.run([str(executable), "run", "hello.snake"], cwd=directory,
                                 env=environment, capture_output=True, text=True, timeout=60)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertIn("7", run.stdout)

            check = subprocess.run([str(executable), "check", str(program)], cwd=directory,
                                   env=environment, capture_output=True, text=True, timeout=60)
            self.assertEqual(check.returncode, 0, check.stderr)
            self.assertIn("OK:", check.stdout)


if __name__ == "__main__":
    unittest.main()
