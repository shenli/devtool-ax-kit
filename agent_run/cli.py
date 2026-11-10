from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from .core import ExecutionStore, ReplayError


def parse_json(value: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def emit(value: Any) -> None:
    print(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False))


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        prog="agent-run",
        description="Capture local evidence and replay recorded tool results without executing them.",
        epilog=(
            "Example: python3 -m agent_run --store /tmp/ax-evidence capture "
            "--workspace . -- python3 -c 'print(42)'\n"
            "Data commands emit JSON on stdout; errors go to stderr. "
            "Place --store before the subcommand."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    root.add_argument(
        "--store",
        default=os.environ.get("AGENT_RUN_STORE", ".agent-runs"),
        help="evidence store (precedence: --store, AGENT_RUN_STORE, .agent-runs)",
    )
    commands = root.add_subparsers(dest="command", required=True)

    capture = commands.add_parser("capture", help="capture a command and workspace checkpoints")
    capture.add_argument("--workspace", default=".")
    capture.add_argument("argv", nargs=argparse.REMAINDER)

    checkpoint = commands.add_parser("checkpoint", help="create a checkpoint")
    checkpoint.add_argument("--run", required=True)
    checkpoint.add_argument("--workspace", default=".")
    checkpoint.add_argument("--label")
    checkpoint.add_argument("--credential-epoch")

    tool = commands.add_parser("record-tool", help="append a tool result to a run")
    tool.add_argument("--run", required=True)
    tool.add_argument("--name", required=True)
    tool.add_argument("--input", required=True)
    tool.add_argument("--output", required=True)
    tool.add_argument("--effect", choices=("read", "write"), default="read")
    tool.add_argument("--receipt")
    tool.add_argument("--authoritative-status")
    tool.add_argument("--identity", help="JSON operation_id, account_id, resource_id, credential_epoch; required for writes")

    replay = commands.add_parser("replay", help="restore a checkpoint with pinned outputs")
    replay.add_argument("--checkpoint", required=True)
    replay.add_argument("--destination")

    replay_tool = commands.add_parser("replay-tool", help="resolve a tool call from a replay")
    replay_tool.add_argument("--replay", required=True)
    replay_tool.add_argument("--name", required=True)
    replay_tool.add_argument("--input", required=True)
    replay_tool.add_argument("--effect", choices=("read", "write"), default="read")
    replay_tool.add_argument("--identity", help="exact identity from the recorded operation")

    inspect = commands.add_parser("inspect", help="emit a run timeline")
    inspect.add_argument("run_id")
    examples = {
        "capture": "capture --workspace . -- python3 -c 'print(42)'",
        "checkpoint": "checkpoint --run RUN_ID --workspace . --label after-change",
        "record-tool": (
            "record-tool --run RUN_ID --name example.read "
            "--input '{}' --output '{\"status\":\"ok\"}'"
        ),
        "replay": "replay --checkpoint CHECKPOINT_ID --destination /tmp/ax-restored",
        "replay-tool": "replay-tool --replay REPLAY_ID --name example.read --input '{}'",
        "inspect": "inspect RUN_ID",
    }
    for name, command_parser in commands.choices.items():
        command_parser.epilog = f"Example: python3 -m agent_run {examples[name]}"
    return root


def main(argv: list[str] | None = None) -> int:
    command_parser = parser()
    args = command_parser.parse_args(argv)
    if args.command == "capture":
        command = list(args.argv)
        if command and command[0] == "--":
            command = command[1:]
        if not command:
            command_parser.error("capture requires a command after --; see capture --help")
    try:
        store = ExecutionStore(args.store, create=args.command not in {"inspect", "replay-tool"})
        if args.command == "capture":
            result = store.capture(args.workspace, command)
            emit(result.__dict__)
            return result.exit_code
        if args.command == "checkpoint":
            emit(
                store.create_checkpoint(
                    args.run,
                    args.workspace,
                    args.label,
                    args.credential_epoch,
                )
            )
            return 0
        if args.command == "record-tool":
            emit(
                store.record_tool(
                    args.run,
                    args.name,
                    parse_json(args.input),
                    parse_json(args.output),
                    effect=args.effect,
                    receipt=parse_json(args.receipt) if args.receipt is not None else None,
                    authoritative_status=args.authoritative_status,
                    identity=parse_json(args.identity) if args.identity is not None else None,
                )
            )
            return 0
        if args.command == "replay":
            emit(store.create_replay(args.checkpoint, args.destination))
            return 0
        if args.command == "replay-tool":
            emit(
                store.replay_tool(
                    args.replay,
                    args.name,
                    parse_json(args.input),
                    effect=args.effect,
                    identity=parse_json(args.identity) if args.identity is not None else None,
                )
            )
            return 0
        if args.command == "inspect":
            emit(store.inspect(args.run_id))
            return 0
    except (KeyError, ValueError, ReplayError, OSError) as error:
        print(f"agent-run: {error}", file=sys.stderr)
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
