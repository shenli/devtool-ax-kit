#!/usr/bin/env python3
"""Synthetic acceptance test for the pinned-replay mechanics.

This deliberately models an ambiguous email send. It is not customer evidence;
it demonstrates what the local spike can and cannot preserve.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from agent_run.core import ExecutionStore, ReplayError


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="agent-replay-spike-") as temporary:
        root = Path(temporary)
        workspace = root / "workspace"
        workspace.mkdir()
        (workspace / "delivery-state.json").write_text(
            json.dumps({"business_event": "welcome/42", "status": "pending"}) + "\n"
        )
        store = ExecutionStore(root / "evidence")
        run_id = store.start_run(
            workspace,
            metadata={"fixture": "ambiguous-resend-timeout", "synthetic": True},
        )
        send_input = {
            "business_event": "welcome/42",
            "idempotency_key": "afs/demo/welcome/42",
            "to": "delivered+demo@resend.dev",
            "payload_hash": "sha256:demo-payload",
        }

        store.record_tool(
            run_id,
            "resend.emails.send",
            send_input,
            {"client_observation": "timeout", "body_received": False},
            effect="write",
            receipt={"email_id": "email_demo_123", "request_id": "request_demo_456"},
            authoritative_status="accepted",
        )
        (workspace / "delivery-state.json").write_text(
            json.dumps({"business_event": "welcome/42", "status": "uncertain"}) + "\n"
        )
        checkpoint = store.create_checkpoint(run_id, workspace, "after-ambiguous-timeout")
        replay = store.create_replay(checkpoint["checkpoint_id"])

        pinned = store.replay_tool(
            replay["replay_id"],
            "resend.emails.send",
            send_input,
            effect="write",
        )
        blocked = False
        try:
            store.replay_tool(
                replay["replay_id"],
                "resend.emails.send",
                {**send_input, "business_event": "welcome/43", "idempotency_key": "afs/demo/welcome/43"},
                effect="write",
            )
        except ReplayError:
            blocked = True

        restored_state = json.loads((Path(replay["workspace"]) / "delivery-state.json").read_text())
        result = {
            "status": "pass" if pinned["executed"] is False and blocked else "fail",
            "scope": "synthetic mechanics only",
            "run_id": run_id,
            "checkpoint_envelope": {
                key: checkpoint[key]
                for key in (
                    "trajectory_offset",
                    "workspace_snapshot_id",
                    "credential_epoch",
                    "effect_ledger_cursor",
                    "policy_hash",
                )
            },
            "restored_workspace_status": restored_state["status"],
            "pinned_original_receipt": pinned["receipt"],
            "pinned_authoritative_status": pinned["authoritative_status"],
            "external_write_reexecuted": pinned["executed"],
            "unrecorded_write_blocked": blocked,
            "comparison": {
                "transcript_plus_workspace": {
                    "visible_client_result": "timeout",
                    "visible_local_status": "uncertain",
                    "can_determine_provider_acceptance": False,
                    "safe_to_repeat_write": False,
                },
                "checkpoint_plus_pinned_effect": {
                    "visible_client_result": "timeout",
                    "visible_local_status": restored_state["status"],
                    "can_determine_provider_acceptance": pinned["authoritative_status"] == "accepted",
                    "safe_to_repeat_write": False,
                    "safe_replay_action": "return original receipt without execution",
                },
            },
            "interpretation": {
                "proved": [
                    "checkpoint restores the failure workspace",
                    "matching external effect returns its original receipt",
                    "replay performs no matching write",
                    "unrecorded external writes are blocked",
                ],
                "not_proved": [
                    "debugging is faster on real failures",
                    "customers want or will pay for replay",
                    "trajectory and workspace need a product-level unified layer",
                    "fork is valuable",
                ],
            },
        }
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
