# DevTool AX Kit

An open toolkit for testing agent experience in Agent-Native developer tools.

It helps you run controlled tasks, compare raw APIs with official agent
surfaces, verify outcomes independently, and measure recovery, side effects,
and credential-handling behavior.

## Included

- append-only agent-run capture;
- content-addressed workspace snapshots and checkpoints;
- receipted external-effect records;
- pinned replay without re-executing writes;
- credential redaction and safety assertions; and
- vendor-neutral failure-report templates.

Read [the AX methodology](docs/agent-ax-methodology.md) for the evaluation
dimensions, session/harness/sandbox model, and research foundation.

## Quick start

Python 3.11+ is sufficient:

```bash
python3 -m unittest discover -s tests -v
python3 scripts/replay_experiment.py
python3 -m agent_run --help
```

## Scope and limits

This is an AX evaluation toolkit, not a security audit tool, credential vault,
sandbox provider, orchestrator, or exact model-replay system.
