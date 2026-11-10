---
name: ax-verification
description: Build and calibrate independent outcome verifiers for developer-tool AX trials.
---

Inputs: frozen manifest, acceptance assertions, final resource references and
evidence. Follow the [experiment protocol](../../docs/experiment-protocol.md)
and [outcome taxonomy](../../docs/outcome-taxonomy.md).

1. Place evaluator code, expected values and evidence outside the evaluated
   agent's writable boundary; a separate path alone does not enforce independence.
   Freeze its hash. Never let the evaluated agent edit it.
2. Calibrate with known-good and known-bad outcomes, including missing state.
   Inspect behavior through a fresh process/client, not the agent's own success test.
3. Check relevant persistence, independent identities, effect counts, scope,
   handoff and cleanup. A receipt of acceptance is not proof of final completion.
4. Return assertion IDs, required flags, expected/observed values and evidence
   references. Use pass/fail/error/not_run; missing or crashed checks cannot pass.
5. Produce a schema-valid result with separate completion, claim and safety.
   Return a nonzero process status on failed or unknown required checks.

For timing-sensitive contracts, predeclare deadlines and observation windows.
Use fresh identities; do not poll by repeating a mutation. For CLI surfaces,
capture raw stdout, stderr and status separately; do not clean output before parsing.
Use [CLI evaluation](../../docs/cli-evaluation.md) for case selection.
The [database calibration](../../taskpacks/databases/README.md) shows a verifier
running outside its task workspace. It is development evidence, not containment proof.
