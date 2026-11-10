#!/usr/bin/env python3
"""Run synthetic reference operations and independent verifier calibration."""
from __future__ import annotations
import hashlib
import json
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agent_run.core import ExecutionStore
from agent_run.protocol import summarize, validate_document

PACK = ROOT / "taskpacks" / "databases"
VERIFIER = PACK / "verify.py"


def check(workspace, mode, marker):
    process = subprocess.run(
        [sys.executable, "-I", str(VERIFIER), str(workspace), "--mode", mode, "--marker", marker],
        capture_output=True, text=True, timeout=10, check=False,
    )
    value = json.loads(process.stdout)
    if process.returncode != (0 if value["status"] == "pass" else 1):
        raise ValueError("verifier exit status disagrees with its assertion")
    return value


def seed(workspace, marker, duplicate=False):
    with sqlite3.connect(workspace / "notes.sqlite") as database:
        database.execute("CREATE TABLE notes (id INTEGER, content TEXT)")
        database.execute("INSERT INTO notes VALUES (1, ?)", (marker,))
        if duplicate:
            database.execute("INSERT INTO notes VALUES (1, ?)", (marker,))


def main():
    manifest = json.loads((PACK / "experiment.json").read_text())
    validate_document(manifest, "experiment", ROOT / "schemas")
    for name, field in (("fixture.json", "fixture_sha256"), ("verify.py", "verifier_sha256")):
        if hashlib.sha256((PACK / name).read_bytes()).hexdigest() != manifest[field]:
            raise ValueError("frozen fixture/verifier changed; revise manifest before running")
    fixture = json.loads((PACK / "fixture.json").read_text())
    first, updated = fixture["initial_marker"], fixture["updated_marker"]
    calibration = []
    results = []
    with tempfile.TemporaryDirectory(prefix="ax-database-pilot-") as temp:
        root = Path(temp)
        for mode in ("first_use", "crud", "recovery", "handoff", "cleanup"):
            for good in (True, False):
                workspace = root / f"calibration-{mode}-{good}"
                workspace.mkdir()
                marker = updated if mode == "crud" else first
                if mode == "cleanup":
                    if not good:
                        seed(workspace, marker)
                else:
                    seed(workspace, marker, duplicate=not good)
                assertion = check(workspace, mode, marker)
                expected = "pass" if good else "fail"
                calibration.append({"mode": mode, "control": "good" if good else "bad",
                                    "expected": expected, "assertion": assertion})
                if assertion["status"] != expected:
                    raise ValueError("verifier calibration failed")
        for repetition in range(manifest["repetitions"]):
            started = time.monotonic()
            workspace = root / f"trial-{repetition}"
            workspace.mkdir()
            store = ExecutionStore(root / f"evidence-{repetition}")
            run = store.start_run(workspace, metadata={"synthetic": True})
            seed(workspace, first)
            identity = {"operation_id": f"insert-{repetition}", "account_id": "local-reference",
                        "resource_id": f"notes-{repetition}", "credential_epoch": "no-credentials"}
            store.record_tool(run, "sqlite.insert", {"id": 1, "content": first},
                              {"client_observation": "timeout"}, effect="write", identity=identity,
                              receipt={"local_commit": "reference-commit-1"}, authoritative_status="committed")
            checks = [check(workspace, "first_use", first)]
            cp = store.create_checkpoint(run, workspace, "committed-response-lost")
            replay = store.create_replay(cp["checkpoint_id"])
            pinned = store.replay_tool(replay["replay_id"], "sqlite.insert", {"id": 1, "content": first},
                                       effect="write", identity=identity)
            if pinned["executed"]:
                raise ValueError("replay executed a write")
            checks.append(check(workspace, "recovery", first))
            with sqlite3.connect(workspace / "notes.sqlite") as database:
                database.execute("UPDATE notes SET content = ? WHERE id = 1", (updated,))
            checks.append(check(workspace, "crud", updated))
            checks.append(check(workspace, "handoff", updated))
            (workspace / "notes.sqlite").unlink()
            checks.append(check(workspace, "cleanup", updated))
            result = {
                "schema_version": 1, "experiment_id": manifest["experiment_id"],
                "run_id": run, "condition_id": "reference-local", "evidence_class": "synthetic",
                "validity": "valid", "completion": "pass", "agent_claim": "none",
                "safety": "pass", "stage": "cleanup",
                "reason": "reference lifecycle completed; no agent or external service",
                "attribution": {"layer": "indeterminate", "confidence": "unknown", "evidence": []},
                "assertions": checks,
                "metrics": {"elapsed_seconds": time.monotonic() - started,
                            "tool_calls": 5, "human_interventions": 0, "cost_usd": None},
                "cleanup": "pass",
            }
            validate_document(result, "result", ROOT / "schemas", manifest)
            results.append(result)
    print(json.dumps({"status": "pass", "scope": "synthetic calibration; no agent-performance claim",
                      "calibration": calibration, "results": results,
                      "summary": summarize(results)}, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
