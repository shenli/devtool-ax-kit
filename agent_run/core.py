from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import stat
import subprocess
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


DEFAULT_POLICY = {
    "external_read": "pinned_only",
    "external_write": "block_unrecorded",
    "recorded_write": "return_original_receipt",
    "credentials": "references_only",
}

IGNORED_PARTS = {
    ".agent-runs",
    ".git",
    ".pytest_cache",
    "__pycache__",
    "node_modules",
}

SECRET_PATTERNS = (
    re.compile(r"(?i)(bearer\s+)[a-z0-9._~+/=-]+"),
    re.compile(r"\bgQ[A-Za-z0-9_-]{20,}\b"),
    re.compile(
        r"(?im)((?:\*{1,2})?(?:api[_-]?key|token|secret|password|authorization)"
        r"\s*:\s*(?:\*{1,2})?\s*(?:\[REDACTED\]\s*)?)([^\s`]+)"
    ),
    re.compile(
        r"(?i)((?:api[_-]?key|token|secret|password|authorization)\s*[:=]\s*)"
        r"([^\s,;\"']+)"
    ),
    re.compile(r"\b(?:re|sk|rk|pk)_[A-Za-z0-9_-]{12,}\b"),
)


class ReplayError(RuntimeError):
    """Raised when replay policy cannot safely satisfy a tool call."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value: bytes | str) -> str:
    if isinstance(value, str):
        value = value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def redact_text(value: str) -> str:
    redacted = value
    for pattern in SECRET_PATTERNS:
        if pattern.groups:
            redacted = pattern.sub(lambda match: f"{match.group(1)}[REDACTED]", redacted)
        else:
            redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def redact(value: Any) -> Any:
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, tuple):
        return [redact(item) for item in value]
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if re.search(r"(?i)(api[_-]?key|token|secret|password|authorization)", str(key)):
                result[str(key)] = "[REDACTED]"
            else:
                result[str(key)] = redact(item)
        return result
    return value


def tool_key(name: str, tool_input: Any) -> str:
    return digest(canonical_json({"name": name, "input": tool_input}))


@dataclass(frozen=True)
class CaptureResult:
    run_id: str
    start_checkpoint: str
    end_checkpoint: str
    exit_code: int
    stdout: str
    stderr: str


class ExecutionStore:
    """Filesystem-backed disposable store for validation experiments.

    Trajectory events are append-only JSONL. Workspace trees are stored by a
    content hash. Checkpoints only correlate those two planes and effect
    receipts; this class intentionally does not pretend they are one engine.
    """

    def __init__(self, root: str | os.PathLike[str] = ".agent-runs") -> None:
        self.root = Path(root).resolve()
        self.runs = self.root / "runs"
        self.objects = self.root / "objects"
        self.checkpoints = self.root / "checkpoints"
        self.replays = self.root / "replays"
        for directory in (self.runs, self.objects, self.checkpoints, self.replays):
            directory.mkdir(parents=True, exist_ok=True)

    def _id(self, prefix: str) -> str:
        return f"{prefix}_{uuid.uuid4().hex[:12]}"

    def _json_write(self, path: Path, value: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n")

    def _json_read(self, path: Path) -> Any:
        return json.loads(path.read_text())

    def start_run(
        self,
        workspace: str | os.PathLike[str],
        command: Iterable[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        workspace_path = Path(workspace).resolve()
        if not workspace_path.is_dir():
            raise ValueError(f"workspace is not a directory: {workspace_path}")
        run_id = self._id("run")
        run_dir = self.runs / run_id
        run_dir.mkdir()
        manifest = {
            "run_id": run_id,
            "created_at": utc_now(),
            "workspace": str(workspace_path),
            "command": redact(list(command or [])),
            "metadata": redact(metadata or {}),
            "environment": {
                "os": platform.system(),
                "architecture": platform.machine(),
                "python": platform.python_version(),
            },
        }
        self._json_write(run_dir / "manifest.json", manifest)
        (run_dir / "trajectory.jsonl").touch()
        return run_id

    def append_event(self, run_id: str, kind: str, payload: dict[str, Any]) -> int:
        trajectory = self.runs / run_id / "trajectory.jsonl"
        if not trajectory.exists():
            raise KeyError(f"unknown run: {run_id}")
        offset = self.event_count(run_id)
        event = {
            "offset": offset,
            "timestamp": utc_now(),
            "kind": kind,
            **redact(payload),
        }
        with trajectory.open("a", encoding="utf-8") as stream:
            stream.write(canonical_json(event) + "\n")
        return offset

    def events(self, run_id: str, limit: int | None = None) -> list[dict[str, Any]]:
        trajectory = self.runs / run_id / "trajectory.jsonl"
        if not trajectory.exists():
            raise KeyError(f"unknown run: {run_id}")
        rows = [json.loads(line) for line in trajectory.read_text().splitlines() if line]
        return rows if limit is None else rows[:limit]

    def event_count(self, run_id: str) -> int:
        trajectory = self.runs / run_id / "trajectory.jsonl"
        if not trajectory.exists():
            raise KeyError(f"unknown run: {run_id}")
        with trajectory.open(encoding="utf-8") as stream:
            return sum(1 for line in stream if line.strip())

    def _workspace_files(self, workspace: Path) -> Iterable[Path]:
        for path in sorted(workspace.rglob("*")):
            relative = path.relative_to(workspace)
            if any(part in IGNORED_PARTS for part in relative.parts):
                continue
            try:
                path.relative_to(self.root)
                continue
            except ValueError:
                pass
            if path.is_file() and not path.is_symlink():
                yield path

    def snapshot(self, workspace: str | os.PathLike[str]) -> str:
        workspace_path = Path(workspace).resolve()
        if not workspace_path.is_dir():
            raise ValueError(f"workspace is not a directory: {workspace_path}")

        entries: list[dict[str, Any]] = []
        sources: list[tuple[Path, str]] = []
        for path in self._workspace_files(workspace_path):
            relative = path.relative_to(workspace_path).as_posix()
            content_hash = digest(path.read_bytes())
            mode = stat.S_IMODE(path.stat().st_mode)
            entries.append(
                {"path": relative, "sha256": content_hash, "size": path.stat().st_size, "mode": mode}
            )
            sources.append((path, relative))

        snapshot_id = digest(canonical_json(entries))
        object_dir = self.objects / snapshot_id
        if not object_dir.exists():
            files_dir = object_dir / "files"
            files_dir.mkdir(parents=True)
            for source, relative in sources:
                destination = files_dir / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
            self._json_write(
                object_dir / "manifest.json",
                {"snapshot_id": snapshot_id, "created_at": utc_now(), "files": entries},
            )
        return snapshot_id

    def restore(self, snapshot_id: str, destination: str | os.PathLike[str]) -> Path:
        object_dir = self.objects / snapshot_id
        manifest_path = object_dir / "manifest.json"
        if not manifest_path.exists():
            raise KeyError(f"unknown snapshot: {snapshot_id}")
        destination_path = Path(destination).resolve()
        if destination_path.exists() and any(destination_path.iterdir()):
            raise ValueError(f"restore destination must be absent or empty: {destination_path}")
        destination_path.mkdir(parents=True, exist_ok=True)
        manifest = self._json_read(manifest_path)
        for entry in manifest["files"]:
            source = object_dir / "files" / entry["path"]
            target = destination_path / entry["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            target.chmod(entry["mode"])
        return destination_path

    def create_checkpoint(
        self,
        run_id: str,
        workspace: str | os.PathLike[str],
        label: str | None = None,
        credential_epoch: str | None = None,
    ) -> dict[str, Any]:
        events = self.events(run_id)
        snapshot_id = self.snapshot(workspace)
        checkpoint_id = self._id("cp")
        effect_cursor = sum(
            1 for event in events if event["kind"] == "tool_result" and event.get("effect") == "write"
        )
        checkpoint = {
            "checkpoint_id": checkpoint_id,
            "run_id": run_id,
            "label": label,
            "trajectory_offset": len(events),
            "workspace_snapshot_id": snapshot_id,
            "credential_epoch": credential_epoch,
            "effect_ledger_cursor": effect_cursor,
            "policy_hash": digest(canonical_json(DEFAULT_POLICY)),
            "created_at": utc_now(),
        }
        self._json_write(self.checkpoints / f"{checkpoint_id}.json", checkpoint)
        self.append_event(run_id, "checkpoint", checkpoint)
        return checkpoint

    def record_tool(
        self,
        run_id: str,
        name: str,
        tool_input: Any,
        output: Any,
        *,
        effect: str = "read",
        receipt: Any | None = None,
        authoritative_status: str | None = None,
    ) -> dict[str, Any]:
        if effect not in {"read", "write"}:
            raise ValueError("effect must be 'read' or 'write'")
        if effect == "write" and receipt is None:
            raise ValueError("external writes require a receipt")
        safe_input = redact(tool_input)
        key = tool_key(name, safe_input)
        self.append_event(
            run_id,
            "tool_intent",
            {"name": name, "input": safe_input, "effect": effect, "tool_key": key},
        )
        result = {
            "name": name,
            "input": safe_input,
            "output": redact(output),
            "effect": effect,
            "receipt": redact(receipt),
            "authoritative_status": authoritative_status,
            "tool_key": key,
        }
        self.append_event(run_id, "tool_result", result)
        return result

    def create_replay(
        self,
        checkpoint_id: str,
        destination: str | os.PathLike[str] | None = None,
    ) -> dict[str, Any]:
        checkpoint_path = self.checkpoints / f"{checkpoint_id}.json"
        if not checkpoint_path.exists():
            raise KeyError(f"unknown checkpoint: {checkpoint_id}")
        checkpoint = self._json_read(checkpoint_path)
        replay_id = self._id("replay")
        replay_dir = self.replays / replay_id
        workspace = Path(destination).resolve() if destination else replay_dir / "workspace"
        self.restore(checkpoint["workspace_snapshot_id"], workspace)
        pinned: dict[str, Any] = {}
        events = self.events(checkpoint["run_id"], checkpoint["trajectory_offset"])
        for event in events:
            if event["kind"] == "tool_result":
                pinned[event["tool_key"]] = {
                    "name": event["name"],
                    "input": event["input"],
                    "output": event["output"],
                    "effect": event["effect"],
                    "receipt": event.get("receipt"),
                    "authoritative_status": event.get("authoritative_status"),
                }
        replay = {
            "replay_id": replay_id,
            "checkpoint_id": checkpoint_id,
            "source_run_id": checkpoint["run_id"],
            "workspace": str(workspace),
            "created_at": utc_now(),
            "policy": DEFAULT_POLICY,
            "pinned": pinned,
        }
        self._json_write(replay_dir / "manifest.json", replay)
        return replay

    def replay_tool(
        self,
        replay_id: str,
        name: str,
        tool_input: Any,
        *,
        effect: str = "read",
    ) -> dict[str, Any]:
        replay_path = self.replays / replay_id / "manifest.json"
        if not replay_path.exists():
            raise KeyError(f"unknown replay: {replay_id}")
        replay = self._json_read(replay_path)
        safe_input = redact(tool_input)
        key = tool_key(name, safe_input)
        if key in replay["pinned"]:
            result = dict(replay["pinned"][key])
            result.update({"source": "pinned", "executed": False})
            return result
        if effect == "write":
            raise ReplayError(f"blocked unrecorded external write: {name}")
        raise ReplayError(f"no pinned output for external read: {name}")

    def capture(
        self,
        workspace: str | os.PathLike[str],
        command: list[str],
        metadata: dict[str, Any] | None = None,
    ) -> CaptureResult:
        if not command:
            raise ValueError("capture command cannot be empty")
        workspace_path = Path(workspace).resolve()
        run_id = self.start_run(workspace_path, command, metadata)
        start = self.create_checkpoint(run_id, workspace_path, "start")
        self.append_event(run_id, "command_intent", {"argv": command})
        process = subprocess.run(
            command,
            cwd=workspace_path,
            capture_output=True,
            text=True,
            check=False,
        )
        stdout = redact_text(process.stdout)
        stderr = redact_text(process.stderr)
        self.append_event(
            run_id,
            "command_result",
            {"exit_code": process.returncode, "stdout": stdout, "stderr": stderr},
        )
        end = self.create_checkpoint(run_id, workspace_path, "end")
        return CaptureResult(
            run_id=run_id,
            start_checkpoint=start["checkpoint_id"],
            end_checkpoint=end["checkpoint_id"],
            exit_code=process.returncode,
            stdout=stdout,
            stderr=stderr,
        )

    def inspect(self, run_id: str) -> dict[str, Any]:
        manifest_path = self.runs / run_id / "manifest.json"
        if not manifest_path.exists():
            raise KeyError(f"unknown run: {run_id}")
        events = self.events(run_id)
        return {
            "manifest": self._json_read(manifest_path),
            "event_count": len(events),
            "events": events,
        }
