# Agent instructions

Read the task prompt, then consult the relevant skill in `skills/`:

- `ax-task-design` for controlled task and fixture design
- `ax-verification` for independent deterministic checks
- `ax-run-capture` for trajectories, checkpoints, receipts, and replay
- `ax-comparison` for raw-vs-official surface comparisons
- `ax-failure-report` for evidence-led vendor reports

The methodology and outcome vocabulary are in `docs/agent-ax-methodology.md`
and `docs/outcome-taxonomy.md`. These are the repository sources of truth.

## Invariants

- Never put real credentials, tokens, production data, or raw secret-bearing
  trajectories in the repository.
- Keep the verifier outside the agent-editable workspace and do not let the
  agent modify it.
- Record external writes only with a stable identity and authoritative receipt.
- Treat unavailable resources separately from functional failures.
- Do not repeat an uncertain external write; use pinned replay and the original
  receipt instead.

## Validation

```bash
python3 -m unittest discover -s tests -v
python3 scripts/replay_experiment.py
```
