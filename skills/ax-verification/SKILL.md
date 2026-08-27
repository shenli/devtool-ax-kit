---
name: ax-verification
description: Build independent, deterministic verifiers for agent-tool tasks.
---

Define assertions outside the agent's editable workspace. Verify observable
behavior, not implementation shape: functional outputs, persistence across a
restart, independent identities, effect counts, and credential absence where
relevant. Return structured pass/fail results with details and a nonzero exit
status on failure.

Run the verifier separately after the agent finishes. Do not let the agent edit
the verifier or turn a missing assertion into a pass. Keep checks local or
explicitly scoped to disposable test resources.

For timing-sensitive behavior, deliberately exercise the boundary and use a
fresh identity per trial. Report valid-trial denominators separately from
infrastructure availability.

Record disagreement between the agent's reported result and the independent
result as a first-class outcome. Exercise timing, restart, duplicate-effect,
and malformed-response boundaries when those are part of the task contract.
