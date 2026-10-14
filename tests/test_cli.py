from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


class CLIContractTest(unittest.TestCase):
    """Exercise the public process boundary with disposable local evidence."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.workspace = self.root / "workspace"
        self.workspace.mkdir()
        self.store = self.root / "evidence"

    def invoke(self, *args: str, env_store: Path | None = None) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPOSITORY_ROOT)
        env.pop("AGENT_RUN_STORE", None)
        if env_store is not None:
            env["AGENT_RUN_STORE"] = str(env_store)
        return subprocess.run(
            [sys.executable, "-m", "agent_run", *args],
            cwd=self.workspace,
            env=env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def evidence_bytes(self) -> dict[str, bytes]:
        return {str(p.relative_to(self.store)): p.read_bytes()
                for p in self.store.rglob("*") if p.is_file()}

    def test_help_at_every_depth_is_successful_without_creating_store(self) -> None:
        for command in ((), ("capture",), ("checkpoint",), ("record-tool",),
                        ("replay",), ("replay-tool",), ("inspect",)):
            with self.subTest(command=command):
                result = self.invoke("--store", str(self.store), *command, "--help")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, "")
                self.assertIn("Example:", result.stdout)
                self.assertFalse(self.store.exists())

    def test_bad_usage_fails_without_prompt_or_store(self) -> None:
        for args in ((), ("unknown",), ("checkpoint",), ("capture",), ("capture", "--")):
            with self.subTest(args=args):
                result = self.invoke("--store", str(self.store), *args)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, "")
                self.assertIn("error:", result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                self.assertFalse(self.store.exists())

    def test_read_commands_do_not_create_missing_store(self) -> None:
        for args in (("inspect", "run_missing"),
                     ("replay-tool", "--replay", "replay_missing", "--name", "read", "--input", "{}")):
            with self.subTest(args=args):
                result = self.invoke("--store", str(self.store), *args)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, "")
                self.assertIn("unknown", result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                self.assertFalse(self.store.exists())

    def test_store_initialization_failure_is_a_diagnostic(self) -> None:
        self.store.write_text("occupied")
        result = self.invoke("--store", str(self.store), "capture", "--", sys.executable, "-c", "pass")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("agent-run:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(self.store.read_text(), "occupied")

    def test_capture_preserves_child_streams_arguments_and_exit_status(self) -> None:
        code = "import sys; print(sys.argv[1:]); print('diagnostic', file=sys.stderr); sys.exit(7)"
        result = self.invoke("--store", str(self.store), "capture", "--", sys.executable,
                             "-c", code, "--help", "two words")
        self.assertEqual(result.returncode, 7)
        self.assertEqual(result.stderr, "")
        payload = json.loads(result.stdout)
        self.assertEqual(payload["exit_code"], 7)
        self.assertEqual(payload["stdout"], "['--help', 'two words']\n")
        self.assertEqual(payload["stderr"], "diagnostic\n")
        before = self.evidence_bytes()
        # A reader must not repair missing directories in an existing store.
        (self.store / "replays").rmdir()
        inspected = self.invoke("--store", str(self.store), "inspect", payload["run_id"])
        self.assertEqual(inspected.returncode, 0, inspected.stderr)
        self.assertEqual(inspected.stderr, "")
        self.assertEqual(json.loads(inspected.stdout)["manifest"]["run_id"], payload["run_id"])
        self.assertEqual(self.evidence_bytes(), before)
        self.assertFalse((self.store / "replays").exists())

    def test_store_selection_uses_flag_then_environment_then_default(self) -> None:
        environment_store = self.root / "environment-evidence"
        for options, env_store, expected in (
            (("--store", str(self.store)), environment_store, self.store),
            ((), environment_store, environment_store),
            ((), None, self.workspace / ".agent-runs"),
        ):
            with self.subTest(expected=expected):
                result = self.invoke(*options, "capture", "--", sys.executable, "-c", "pass",
                                     env_store=env_store)
                self.assertEqual(result.returncode, 0, result.stderr)
                run_id = json.loads(result.stdout)["run_id"]
                self.assertTrue((expected / "runs" / run_id / "manifest.json").is_file())
                if options:
                    self.assertFalse(environment_store.exists())


if __name__ == "__main__":
    unittest.main()
