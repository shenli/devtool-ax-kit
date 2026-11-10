---
name: ax-task-design
description: Design controlled developer-tool AX experiments, fixtures and task packs for onboarding, use and recovery comparisons.
---

Use the [experiment protocol](../../docs/experiment-protocol.md) to freeze a
manifest before trials. Inputs are the workflow, supported product contract,
candidate surfaces, resource boundary and evaluation budget.

1. Choose cold-start onboarding or configured-resource use. A signup barrier is
   measured behavior in the former and may be a prerequisite failure in the latter.
2. Choose unassisted discovery or guided use. Supply acceptance criteria without
   revealing the solution path when discoverability is being measured.
3. Write the exact prompt, minimal realistic fixture, allowed effects, stage
   milestones and stop conditions. Include restart/boundary assertions for durable
   state; distinguish temporary access, ownership handoff and cleanup.
4. Freeze fixture/evaluator hashes, condition versions, repetitions, randomized
   order seed, reset policy, intervention limits and analysis. Separate development
   fixtures from held-out cases.
5. Validate the manifest with `scripts/validate_protocol.py`. Deliver the manifest,
   prompt, fixture, evaluator contract and calibration cases; no trial is implied.

For CLI cases, use [CLI evaluation](../../docs/cli-evaluation.md) for stream,
configuration and argument assertions. For database examples, use the
[database task pack](../../taskpacks/databases/README.md).
Stop design when the required resource or assertion cannot be specified; record
the missing prerequisite instead of weakening success criteria.
