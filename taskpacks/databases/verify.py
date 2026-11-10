#!/usr/bin/env python3
"""Independent local SQLite verifier. Keep outside the evaluated writable tree."""
import argparse
import json
import sqlite3
from pathlib import Path


def verify(workspace: Path, mode: str, marker: str) -> dict:
    database = workspace / "notes.sqlite"
    evidence = f"sqlite-verifier:{mode}"
    expected = "database and SQLite sidecars absent" if mode == "cleanup" else "exactly one row with expected marker; one database"
    try:
        databases = list(workspace.rglob("*.sqlite"))
        if mode == "cleanup":
            leftovers = list(workspace.rglob("*.sqlite*"))
            status = "pass" if not leftovers else "fail"
            observed = f"{len(leftovers)} database artifacts remain"
        elif not database.is_file() or database.is_symlink():
            status, observed = "fail", "required database missing or symbolic link"
        else:
            # mode=ro prevents a missing database from being created by verification.
            connection = sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True)
            try:
                rows = connection.execute("SELECT id, content FROM notes ORDER BY id").fetchall()
            finally:
                connection.close()
            status = "pass" if rows == [(1, marker)] and len(databases) == 1 else "fail"
            observed = f"row_count={len(rows)}; matching_rows={sum(row == (1, marker) for row in rows)}; database_count={len(databases)}"
        return {"id": mode, "required": True, "status": status, "expected": expected,
                "observed": observed, "evidence": [evidence]}
    except (OSError, sqlite3.Error):
        return {"id": mode, "required": True, "status": "error", "expected": expected,
                "observed": "independent database inspection could not complete",
                "evidence": [evidence]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace", type=Path)
    parser.add_argument("--mode", choices=("first_use", "crud", "recovery", "handoff", "cleanup"), required=True)
    parser.add_argument("--marker", default="ax-fixture-first")
    args = parser.parse_args()
    if not args.workspace.is_dir():
        parser.error("workspace must exist")
    result = verify(args.workspace, args.mode, args.marker)
    print(json.dumps(result))
    return 0 if result["status"] == "pass" else 1

if __name__ == "__main__":
    raise SystemExit(main())
