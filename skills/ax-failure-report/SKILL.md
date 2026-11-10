---
name: ax-failure-report
description: Turn replicated AX findings into private evidence-led vendor reports and regression candidates.
---

Inputs: frozen protocol, repeated results, independent assertions and redacted
evidence. Use the [report template](../../docs/failure-report-template.md).

1. Lead with observed behavior and impact, then frequency and uncertainty.
   Separate observation from causal attribution and describe non-reproductions.
2. Include task/fixture/verifier versions and hashes, run IDs, surface conditions,
   budgets, interventions, stopping stage and all denominator exclusions.
3. Use the [shared taxonomy](../../docs/outcome-taxonomy.md). Record functional,
   safety and claim outcomes separately, with attribution confidence and evidence.
4. Propose the smallest contract-preserving fix and executable regression case.
   Verify the fix on development cases and reserve held-out cases for broader claims.
5. State freshness, evidence provenance and limits. Ask the vendor to confirm
   the supported contract or reproduce the failure, not endorse a thesis.

Deliver a private draft and evidence index. Do not transmit it without authorization.
Never attach credentials, claim URLs, raw secret-bearing trajectories or unbounded logs.
If repetition or independent verification is missing, label the finding preliminary.
Do not assign undefined E0–E6 grades; describe synthetic, observed or replicated evidence.
