from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agent_run.core import ExecutionStore, ReplayError, redact


class ExecutionStoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.workspace = self.root / "workspace"
        self.workspace.mkdir()
        self.store = ExecutionStore(self.root / "evidence")
        self.identity = {"operation_id": "op-1", "account_id": "test-account",
                         "resource_id": "test-resource", "credential_epoch": "epoch-1"}

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
            identity=self.identity,
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
            identity=self.identity,
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
                identity=self.identity,
            )

    def test_secret_values_are_redacted_from_trajectory(self) -> None:
        run_id = self.store.start_run(self.workspace)
        self.store.record_tool(
            run_id,
            "service.inspect",
            {"credential_ref": "test-credential"},
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


    def test_snapshot_excludes_credentials_and_preserves_safe_bytes(self) -> None:
        (self.workspace / ".env").write_text("DATABASE_URL=synthetic-private-value")
        (self.workspace / ".env.local").write_text("synthetic-private-value")
        (self.workspace / "safe.txt").write_bytes(b"exact bytes\x00")
        snapshot = self.store.snapshot(self.workspace)
        destination = self.root / "restored"
        self.store.restore(snapshot, destination)
        self.assertFalse((destination / ".env").exists())
        self.assertFalse((destination / ".env.local").exists())
        self.assertEqual((destination / "safe.txt").read_bytes(), b"exact bytes\x00")
        manifest = json.loads((self.store.objects / snapshot / "manifest.json").read_text())
        self.assertEqual(manifest["excluded"], [".env", ".env.local"])
        self.assertNotIn(b"synthetic-private-value", b"".join(
            p.read_bytes() for p in self.store.root.rglob("*") if p.is_file()))

    def test_secret_snapshot_fails_before_persisting_any_file(self) -> None:
        for content in ('postgresql://demo:synthetic-value@localhost/test',
                        '{"connectionString": "synthetic-value"}'):
            with self.subTest(content=content):
                (self.workspace / "a-safe.txt").write_text("safe")
                (self.workspace / "z-config.txt").write_text(content)
                with self.assertRaisesRegex(ValueError, "suspected secret"):
                    self.store.snapshot(self.workspace)
                self.assertEqual(list(self.store.objects.iterdir()), [])

    def test_connection_and_claim_urls_are_redacted(self) -> None:
        self.assertEqual(redact({"connectionString": "synthetic-value", "claimUrl": "private-link"}),
                         {"connectionString": "[REDACTED]", "claimUrl": "[REDACTED]"})
        for value in ("postgresql://u:synthetic-value@localhost/db",
                      "https://example.test/claim?token=synthetic-value"):
            self.assertNotIn("synthetic-value", redact(value))

    def test_secret_inputs_rejected_without_lossy_matching(self) -> None:
        run = self.store.start_run(self.workspace)
        for value in ("synthetic-A", "synthetic-B", "[REDACTED]"):
            with self.assertRaisesRegex(ValueError, "credential references"):
                self.store.record_tool(run, "read", {"password": value}, {})
        self.assertEqual(self.store.events(run), [])

    def test_identity_isolation_and_idempotent_evidence_ingestion(self) -> None:
        run = self.store.start_run(self.workspace)
        kwargs = dict(effect="write", identity=self.identity, receipt={"id": "receipt-1"},
                      authoritative_status="accepted")
        self.store.record_tool(run, "write", {"value": 1}, {}, **kwargs)
        self.store.record_tool(run, "write", {"value": 1}, {}, **kwargs)
        self.assertEqual(len(self.store.events(run)), 2)
        with self.assertRaisesRegex(ValueError, "different evidence"):
            self.store.record_tool(run, "write", {"value": 2}, {}, **kwargs)
        second = {**self.identity, "operation_id": "op-2"}
        self.store.record_tool(run, "write", {"value": 1}, {}, **{**kwargs,
                               "identity": second, "receipt": {"id": "receipt-2"}})
        replay = self.store.create_replay(self.store.create_checkpoint(run, self.workspace)["checkpoint_id"])
        for identity, receipt in ((self.identity, "receipt-1"), (second, "receipt-2")):
            result = self.store.replay_tool(replay["replay_id"], "write", {"value": 1},
                                            effect="write", identity=identity)
            self.assertEqual(result["receipt"]["id"], receipt)
            self.assertFalse(result["executed"])
        for field in self.identity:
            with self.subTest(field=field), self.assertRaises(ReplayError):
                self.store.replay_tool(replay["replay_id"], "write", {"value": 1},
                                      effect="write", identity={**self.identity, field: "different"})
        with self.assertRaises(ReplayError):
            self.store.replay_tool(replay["replay_id"], "write", {"value": 1},
                                  effect="read", identity=self.identity)

    def test_missing_identity_and_receipt_are_rejected(self) -> None:
        run = self.store.start_run(self.workspace)
        for kwargs in ({"receipt": {"id": "r"}, "authoritative_status": "accepted"},
                       {"identity": self.identity},
                       {"identity": self.identity, "receipt": {}}):
            with self.assertRaises(ValueError):
                self.store.record_tool(run, "write", {}, {}, effect="write", **kwargs)
        self.assertEqual(self.store.events(run), [])

    def test_repeated_reads_and_legacy_evidence_fail_closed(self) -> None:
        run = self.store.start_run(self.workspace)
        self.store.record_tool(run, "read", {}, {"state": "before"})
        self.store.record_tool(run, "read", {}, {"state": "after"})
        cp = self.store.create_checkpoint(run, self.workspace)
        replay = self.store.create_replay(cp["checkpoint_id"])
        with self.assertRaisesRegex(ReplayError, "ambiguous"):
            self.store.replay_tool(replay["replay_id"], "read", {})
        self.store.append_event(run, "tool_result", {"name": "legacy"})
        cp = self.store.create_checkpoint(run, self.workspace)
        with self.assertRaisesRegex(ReplayError, "legacy"):
            self.store.create_replay(cp["checkpoint_id"])


if __name__ == "__main__":
    unittest.main()
