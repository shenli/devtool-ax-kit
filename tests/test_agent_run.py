from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agent_run.core import ExecutionStore, ReplayError


class ExecutionStoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.workspace = self.root / "workspace"
        self.workspace.mkdir()
        self.store = ExecutionStore(self.root / "evidence")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_snapshot_is_content_addressed_and_restorable(self) -> None:
        source = self.workspace / "src" / "example.txt"
        source.parent.mkdir()
        source.write_text("known-good\n")

        first = self.store.snapshot(self.workspace)
        second = self.store.snapshot(self.workspace)
        self.assertEqual(first, second)

        source.write_text("mutated\n")
        destination = self.root / "restored"
        self.store.restore(first, destination)
        self.assertEqual((destination / "src" / "example.txt").read_text(), "known-good\n")

    def test_replay_returns_receipt_without_execution_and_blocks_new_write(self) -> None:
        (self.workspace / "state.json").write_text('{"status":"uncertain"}\n')
        run_id = self.store.start_run(self.workspace)
        sent_input = {"event": "welcome/42", "to": "delivered+42@resend.dev"}
        self.store.record_tool(
            run_id,
            "resend.emails.send",
            sent_input,
            {"client_observation": "timeout"},
            effect="write",
            receipt={"email_id": "email_123"},
            authoritative_status="accepted",
        )
        checkpoint = self.store.create_checkpoint(run_id, self.workspace, "after-timeout")
        replay = self.store.create_replay(checkpoint["checkpoint_id"])

        pinned = self.store.replay_tool(
            replay["replay_id"],
            "resend.emails.send",
            sent_input,
            effect="write",
        )
        self.assertFalse(pinned["executed"])
        self.assertEqual(pinned["source"], "pinned")
        self.assertEqual(pinned["receipt"]["email_id"], "email_123")
        self.assertEqual(pinned["authoritative_status"], "accepted")

        with self.assertRaisesRegex(ReplayError, "blocked unrecorded external write"):
            self.store.replay_tool(
                replay["replay_id"],
                "resend.emails.send",
                {"event": "welcome/43", "to": "delivered+43@resend.dev"},
                effect="write",
            )

    def test_secret_values_are_redacted_from_trajectory(self) -> None:
        run_id = self.store.start_run(self.workspace)
        self.store.record_tool(
            run_id,
            "service.inspect",
            {"authorization": "Bearer secret-value-123"},
            "token=top-secret-value\n**Token:** markdown-secret-value\n"
            "**Token:[REDACTED] gQAAAAAAExampleTemporaryToken123456789",
        )
        serialized = json.dumps(self.store.events(run_id))
        self.assertNotIn("secret-value-123", serialized)
        self.assertNotIn("top-secret-value", serialized)
        self.assertNotIn("markdown-secret-value", serialized)
        self.assertNotIn("gQAAAAAAExampleTemporaryToken123456789", serialized)
        self.assertIn("[REDACTED]", serialized)

    def test_capture_seals_start_and_end_workspace_states(self) -> None:
        script = self.workspace / "change.py"
        script.write_text("from pathlib import Path\nPath('result.txt').write_text('done\\n')\nprint('ok')\n")
        result = self.store.capture(self.workspace, ["python3", "change.py"])
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.stdout, "ok\n")

        replay = self.store.create_replay(result.start_checkpoint)
        restored = Path(replay["workspace"])
        self.assertFalse((restored / "result.txt").exists())
        self.assertTrue((self.workspace / "result.txt").exists())


if __name__ == "__main__":
    unittest.main()
