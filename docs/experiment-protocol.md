# Reproducible AX experiments

Use this protocol with the five skills. The machine-readable contracts are
[experiment](../schemas/experiment.schema.json) and [result](../schemas/result.schema.json).
They use JSON Schema 2020-12; the dependency-free validator implements only the
keywords used here and rejects unsupported keywords.

## Freeze before running

Record the exact prompt, fixture and evaluator SHA-256 hashes, model and harness
versions, tool/Skill/MCP versions, resource limits, network access, deadlines,
tool-call and cost budgets, repetition count, reset policy and run-order seed.
Declare the allowed interventions and stop rule before seeing results. Each
trial starts with fresh state and a unique run identity; use unique external
namespaces and provider-supported disposable resources.

Select one track:
- `cold_start`: begin without an account/resource; signup, access and provision
  are measured behavior. Primary metric is end-to-end completion.
- `configured_resource`: an evaluator provisions the resource first; test
  functionality conditional on that prerequisite being usable.

Product access barriers in a cold-start task are valid failures of that journey,
not excluded infrastructure failures. A broken evaluator inbox or sandbox is an
exclusion only when supported by evidence. Preserve uncertain causes as unknown.
Declare prerequisites narrowly so exclusions cannot erase the behavior under study.

Select discovery conditions separately from execution surfaces:
- `unassisted`: a goal and vendor identity; measure whether the agent discovers
  the supported route. Do not leak the solution in recovery instructions.
- `guided`: provide a documented entry point or installed official skill.
  Record exactly what was supplied and whether the skill/tool was actually used.

A change in discovery information and surface together measures the combined
experience. It does not isolate the causal effect of the surface alone.

## Task packs and evaluator independence

Each pack contains a prompt, starting fixture, allowed effects, assertions,
stop conditions and calibration cases. The evaluated agent sees only its task
workspace. Mount the evaluator, expected results and evidence store outside
that workspace and make them inaccessible to writes by the evaluated agent.
A different directory alone is not an access-control boundary.

Run known-good and known-bad controls before trials. Evaluate final state
through a fresh client/process, not through the agent's own tests or claims.
Keep evaluator errors and missing checks as unknown. Version and hash the
evaluator before trials; changes require a new protocol version and rerun of
affected conditions. The repository's unit tests are development checks.

## Repetitions and comparisons

Choose repetitions for the precision needed; there is no universal minimum.
A three-run pilot can find failures but cannot establish a reliable ranking.
Pair conditions by task and fixture, randomize order using the recorded seed,
and reset accounts/resources/context between trials. Reuse neither successful
workspaces nor an uncertain external write. Pinned replay inspects evidence;
it is not a fresh trial.

Report per-condition counts, excluded counts and reasons, unknown completion,
functional completion, safe completion, claim disagreement and human effort.
The built-in summary reports counts and rates only, not statistical significance.
Never average percentages without declaring weighting. For suites, distinguish
equal-task averages from pooled-trial averages and show the underlying cells.

For inferential reports, predeclare the analysis: paired differences and
confidence intervals resampled at the independent unit (often task or account),
not individual tool calls. Group shared outage/time blocks when relevant.
Declare multiplicity correction for multiple comparisons. Do not claim a
ranking from overlapping, sparse estimates. Repeated reliability (`pass^k`)
is distinct from success in any of k attempts (`pass@k`); never silently assume
independent trials or estimate suite reliability by exponentiating a pooled rate.

Keep improvement/development cases separate from held-out evaluation cases.
Report resource guarantees and ceilings, concurrency, execution dates, outages,
model settings, cache state and measured costs. Missing cost is null, not zero.

## Journey and lifecycle evidence

Record discovery, access, provision, first use, independent verification,
handoff and cleanup separately. A step event should include run ID, UTC time,
stage, observed status, evidence reference and any intervention. These are
recommended `append_event` payloads, not an automatically instrumented adapter.
Likewise token usage, costs and service receipts must come from the harness or
provider; do not infer them from narrative text.

A working temporary resource, a successfully claimed resource and durable
readiness are different contracts. Declare which is required, including TTL,
ownership readback and cleanup. Count unexpected resources independently from
functional success. Never treat cancellation as proof that a write did not occur.

## Validate

```bash
python3 scripts/validate_protocol.py taskpacks/databases/experiment.json
python3 scripts/database_pilot.py
python3 scripts/validate_skills.py
```

The database pilot calibrates local mechanics using reference operations.
It runs no coding agent and supplies no evidence about hosted-product usability.
Live trials need independently provisioned test infrastructure, supported signup
paths and declared limits. This protocol grants no permission to create external
accounts, bypass access barriers or spend money.
