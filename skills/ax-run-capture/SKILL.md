---
name: ax-run-capture
description: Capture AX trial evidence, checkpoints and authoritative effect receipts for safe inspection and pinned replay.
---

Inputs: frozen experiment, unique run ID, minimal secret-free workspace,
external resource references and an evidence store outside the evaluated agent's
write access. Read [evidence safety](../../docs/evidence-safety.md) before capture.

1. Record model/harness/tool versions, UTC start/end times, actual resource limits
   and interventions. Use `agent_run` for snapshots and events; adapters must supply
   tool trajectories, provider receipts and measured usage.
2. Capture discovery, access, provision, first use, verify, handoff and cleanup
   separately. Retain evidence references for both progress and stops.
3. Use opaque credential references. Writes require operation/account/resource/
   credential-epoch identity, authoritative status and a nonempty receipt.
   Reuse identity for evidence ingestion retries, not for a different operation.
4. If a write is uncertain and has no receipt, record the unresolved observation.
   Reconcile with a supported status read; never repeat the write to fill the gap.
5. Seal the checkpoint and validate the result. Scan evidence before sharing.
   Snapshot exclusions must be visible; excluded credentials are not restored.

Pinned replay is a non-executing lookup of original evidence, not a new trial or
a guarantee that unrelated caller tools cannot write. Run it without network access.
Stop on secret detection, identity conflict or missing authoritative evidence.
Classify availability using the experiment's track and the
[outcome taxonomy](../../docs/outcome-taxonomy.md), not blanket exclusion of signup failures.
