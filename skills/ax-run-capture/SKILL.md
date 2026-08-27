---
name: ax-run-capture
description: Capture agent runs with checkpoints, effect receipts, and redacted trajectories.
---

Use the local `agent_run` package to capture the command, starting and ending
workspace snapshots, trajectory events, and checkpoints. Record external writes
only with an authoritative receipt and stable effect identity. Redact secrets
before persistence and scan the resulting evidence.

When a write has an uncertain outcome, do not repeat it blindly: pin the prior
receipt and replay it as a non-executing lookup. Block unrecorded writes during
replay. Keep credentials out of prompts, source files, snapshots, and reports.

For external services, capture provisioning, credential delivery, execution,
verification, and cleanup as separate lifecycle receipts. If a resource cannot
be retrieved, record `resource_unavailable` and stop that trial.
