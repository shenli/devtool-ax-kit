import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

VERIFIER = Path(__file__).resolve().parents[1] / "taskpacks/databases/verify.py"


class DatabaseVerifierTest(unittest.TestCase):
    def test_missing_or_corrupt_database_never_passes_or_gets_created(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            def check():
                result = subprocess.run([sys.executable, "-I", str(VERIFIER), str(workspace),
                                         "--mode", "first_use"], capture_output=True, text=True, timeout=10)
                self.assertEqual(result.returncode, 1, result.stderr)
                return json.loads(result.stdout)
            self.assertEqual(check()["status"], "fail")
            self.assertFalse((workspace / "notes.sqlite").exists())
            (workspace / "notes.sqlite").write_bytes(b"not a sqlite database")
            self.assertEqual(check()["status"], "error")

    def test_fresh_readback_does_not_mutate_database(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            database = workspace / "notes.sqlite"
            with sqlite3.connect(database) as connection:
                connection.execute("CREATE TABLE notes (id INTEGER, content TEXT)")
                connection.execute("INSERT INTO notes VALUES (1, 'ax-fixture-first')")
            before = {p.name: p.read_bytes() for p in workspace.iterdir()}
            result = subprocess.run([sys.executable, "-I", str(VERIFIER), str(workspace),
                                     "--mode", "handoff"], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["status"], "pass")
            self.assertEqual(before, {p.name: p.read_bytes() for p in workspace.iterdir()})
