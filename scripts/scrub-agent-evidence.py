#!/usr/bin/env python3
"""Reapply current redaction rules to local agent evidence atomically."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]
if str(REPOSITORY) not in sys.path:
    sys.path.insert(0, str(REPOSITORY))

from agent_run.core import redact_text


def main() -> int:
    evidence = REPOSITORY / "evidence"
    changed = 0
    for path in evidence.rglob("*.jsonl"):
        original = path.read_text()
        redacted = redact_text(original)
        if redacted == original:
            continue
        descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        try:
            with os.fdopen(descriptor, "w") as stream:
                stream.write(redacted)
            os.chmod(temporary, 0o600)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        changed += 1
    print(f"Scrubbed {changed} evidence file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
