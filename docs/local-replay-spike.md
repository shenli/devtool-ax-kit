# Local pinned-replay spike

**Evidence class:** synthetic implementation evidence; does not count as E3 customer evidence  
**Command:** `python3 scripts/replay_experiment.py`

## Hypothesis under test

A minimal checkpoint envelope can correlate a restored workspace with an append-only trajectory and effect receipt, allowing replay to inspect an ambiguous external write without repeating it.

## Fixture

The local state says a welcome email is pending. A synthetic Resend adapter records an accepted provider receipt but returns a client-timeout observation. The application writes `uncertain` locally and the run seals a checkpoint.

## Assertions

1. Restoring the checkpoint reproduces local `uncertain` state.
2. Replaying the exact send returns the original provider receipt and `accepted` status with `executed=false`.
3. Attempting a different, unrecorded send is blocked.
4. The checkpoint records trajectory offset, workspace snapshot, effect cursor, credential epoch, and policy hash.

## Executed result — 2026-08-27

Status: **pass**

```text
restored workspace status: uncertain
effect ledger cursor: 1
pinned authoritative status: accepted
pinned receipt: email_demo_123 / request_demo_456
matching external write executed: false
unrecorded external write blocked: true
```

In the synthetic transcript-plus-workspace condition, the available observations are `timeout` and local `uncertain`; provider acceptance cannot be determined. Adding the pinned effect record exposes the original accepted receipt while keeping the safe action “return receipt without execution.” Neither condition makes repeating an email write safe. This is a deterministic contrast in evidence completeness, not a measured human debugging-time improvement.

The unit suite also passed all four storage, restore, replay-policy, redaction, and capture tests. A CLI smoke run captured that suite as `run_1f66990b86a4`, sealed start checkpoint `cp_34417039172c` and end checkpoint `cp_06c5bac9f5e1`, and restored the start checkpoint as `replay_2a127bd73831`. These IDs refer to local ignored evidence under `.agent-runs/` and are not durable published evidence.

## Interpretation rule

A pass validates cheap implementation of the mechanics and safety policy only. It is not evidence that replay improves real debugging, that a buyer exists, that the two planes need physical unification, or that `fork()` should be built.

The redaction rules are defense-in-depth patterns, not a production secret scanner. Real external-run intake still requires participant-side redaction and a human review before sharing evidence.
