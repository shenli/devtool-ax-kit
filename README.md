# DevTool AX Kit

**Measure whether developer tools are understandable, recoverable, and
verifiable for coding agents.**

DevTool AX Kit is a small, local-first toolkit for testing Agent-Native
developer tools. It captures what happened, verifies what actually happened,
and makes ambiguous external effects safe to inspect without repeating them.

## Why this exists

Agent success is more than “the model produced code.” A useful evaluation asks:

- Could the agent find the right instructions and interfaces?
- Could it recover after an ambiguous tool response?
- Did an independent verifier agree with its success claim?
- Were retries, credentials, and external side effects contained?

## What you get

| Capability | Use it to measure |
|---|---|
| Run capture and snapshots | What the agent saw and changed |
| Checkpoints and pinned replay | Whether uncertain work can be resumed safely |
| Effect receipts | Whether an external write is identified and recoverable |
| Redaction and safety assertions | Whether evidence can be shared safely |
| AX skills and templates | How to design, verify, compare, and report tasks |

## Quick start

Requires Python 3.11 or newer. No runtime dependencies are required.

```bash
git clone https://github.com/shenli/devtool-ax-kit.git
cd devtool-ax-kit
python3 -m unittest discover -s tests -v
python3 scripts/replay_experiment.py
python3 -m agent_run --help
```

Capture a local command:

```bash
python3 -m agent_run capture --workspace /path/to/workspace -- python3 -m unittest
```

Record a receipted effect, then replay it without executing the write:

```bash
python3 -m agent_run record-tool --run RUN_ID \
  --name example.send --input '{"event":"welcome/42"}' \
  --output '{"status":"accepted"}' --effect write \
  --receipt '{"request_id":"demo-123"}' --authoritative-status accepted
python3 -m agent_run checkpoint --run RUN_ID --workspace /path/to/workspace --label after-write
python3 -m agent_run replay --checkpoint CHECKPOINT_ID
```

Pinned replay returns the original receipt without executing the write; an
unrecorded write is rejected.

## Repository map

```text
agent_run/                  capture, snapshots, checkpoints, replay
skills/                     reusable AX evaluation instructions
docs/                       methodology, taxonomy, and report templates
tests/                      local regression tests
scripts/replay_experiment.py synthetic mechanics demonstration
```

Start with [`AGENTS.md`](AGENTS.md), then choose the relevant skill under
[`skills/`](skills/). The [documentation index](docs/README.md) links the
methodology and example artifacts.

## Scope

This is evaluation instrumentation—not a credential vault, sandbox provider,
orchestrator, security audit, or exact model-replay system. Keep experiments
local or use disposable test resources, and run independent verification
outside the agent's editable workspace.

## Contributing

Keep tasks vendor-neutral, verifiers deterministic, and evidence reproducible.
Run the unit tests and skill validators before opening a pull request. See
[`SECURITY.md`](SECURITY.md) before sharing trajectories or external-run data.
