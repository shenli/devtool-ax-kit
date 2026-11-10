# Evaluating a CLI surface

Use this protocol alongside the [AX methodology](agent-ax-methodology.md).
Measure whether a caller can discover, execute, and verify a particular task
through a CLI. A style preference alone is not a functional failure. Define
the task's contract before running it.

## Freeze the experiment

Record the executable version or commit, fixture hash, working directory,
argument array, relevant environment overrides, and a time budget. Record
whether each of stdin, stdout, and stderr is connected to a terminal, a pipe,
a file, or a closed input. Do not infer all three from one stream.

Use synthetic payloads and disposable resources. Put the verifier and its
expected results outside the evaluated agent's editable workspace. Keep the
same fixture, assertions, and budget when comparing CLI, Skill, or MCP access.
Repository unit tests are development checks; they do not by themselves prove
independence in an agent evaluation.

## Choose observable assertions

Select cases relevant to the tool and task rather than assigning a universal
style score. Each case needs its own expected exit status, stream contents,
state changes, and stop condition.

| Experiment | Evidence to retain | Independent assertion |
|---|---|---|
| Discover a command from help | Help output and commands attempted | The advertised invocation works against the frozen fixture; help leaves fixture and evidence unchanged. |
| Run with stdin closed | Exit status, separate output streams, elapsed time | Required input is accepted through the documented arguments, or the invocation terminates with a useful diagnostic within budget. |
| Pipe a successful result to a parser | Raw stdout and stderr, parsed result | The promised data format parses without stripping banners or diagnostics; required values have the documented types. |
| Request an absent identity or an empty collection | Result, status, fixture inventory | The tool distinguishes the two according to its documented contract; a failed lookup cannot be mistaken for a completed task. |
| Read existing state, then read missing state | Directory inventory and content hashes before/after | A read does not create, repair, or change evidence or the target fixture. |
| Supply conflicting configuration sources | Explicit flag and synthetic environment settings, selected resource | The documented source wins; the command does not silently act on another resource. |
| Pass option-like values through a command wrapper | Child-observed argument array | Arguments after the separator retain their order and values. |
| Lose a write response after acceptance | Stable effect identity, authoritative receipt, local observation | Verification establishes the effect count; replay returns the recorded receipt without another write. |
| Interrupt or time out a mutation | Last checkpoint, receipt if available, resulting state | Report the observed state and uncertainty; never infer that cancellation undid a write. |

For terminal-dependent interfaces, repeat relevant cases with mixed stream
connections, especially piped stdout with terminal stderr and closed stdin.
If the harness cannot supply a required terminal or test resource, record the
limitation explicitly rather than claiming coverage. Stop a hung local process
at the declared deadline; do not use the deadline as a reason to retry an
external mutation.

## Classify the result

Use the existing [outcome taxonomy](outcome-taxonomy.md), not a separate CLI
severity vocabulary. Keep evaluator-prerequisite failures outside valid-trial denominators;
product access barriers remain valid outcomes in cold-start experiments. Record an agent's success claim separately from the verifier's
result. A malformed payload or a hang on a usable fixture can be a
`functional_fail`; an out-of-scope write can be a `safety_violation`.

Capture assertion-level actual/expected values and evidence paths. Do not
convert a missing assertion into a pass. State which cases were not exercised.
If a write is uncertain, follow the existing receipt and pinned-replay rules.

## The kit's current CLI contract

Run `python3 -m agent_run --help` for discovery. The installed `devtool-ax`
entry point uses the same implementation. Help examples use the module form;
identity placeholders must be replaced with values returned by prior commands.

- Put global `--store PATH` before the subcommand. Store selection is explicit
  flag, then `AGENT_RUN_STORE`, then `.agent-runs` relative to the current directory.
- Data commands emit one JSON value on stdout. CLI diagnostics go to stderr.
  Help is text on stdout and exits 0. Missing commands or arguments exit 2.
- `capture -- COMMAND ...` includes the child's stdout and stderr as JSON
  fields and returns the child's normal exit code. A nonzero capture status can
  therefore accompany valid JSON evidence; it is not necessarily a CLI error.
- Handled store, input, and replay-policy errors exit 2 with a text diagnostic.
  This code does not distinguish missing evidence from a policy rejection.
- `inspect` and `replay-tool` do not initialize store directories. A missing
  identity fails without creating an empty store. `create=False` on the Python
  store constructor suppresses initialization; it is not a write-protection
  capability for other methods.
- `replay` restores files and writes a replay manifest. It is a local mutation;
  `replay-tool` only looks up pinned results and never invokes an external tool.
- The wrapper has no interactive prompts, progress rendering, or network calls
  of its own. A captured child can have any of those behaviors and inherits
  stdin. This wrapper is not a sandbox or a timeout supervisor.

`tests/test_cli.py` checks piped execution, help, invalid input, store selection,
initialization errors, read-only inspection, and child argument/output handling.
The core tests and `scripts/replay_experiment.py` cover receipt reuse and blocked
unrecorded writes. These are local regression checks, not a claim that all
terminal, signal, concurrency, or external-service cases have been evaluated.

## Reference and provenance

This review was informed by Steve Francia (spf13), spf13 labs LLC, and
contributors' [CLI Style](https://cli.style/), reviewed at
[`spf13/cli-style` commit `0e365ea`](https://github.com/spf13/cli-style/tree/0e365eaceb5f652b9ade24497146e93bcc099601).
This protocol is written around this kit's fixtures, evidence, and outcome
taxonomy; it does not reproduce the upstream guide, principle list, or skill.
See [third-party notices](../THIRD_PARTY_NOTICES.md) for the license boundary.

## Identity and snapshot changes

Writes now require `--identity` with operation_id, account_id, resource_id and
credential_epoch, plus a nonempty receipt and authoritative status. The same
identity is required for lookup. Detected secret-bearing inputs are rejected;
use credential references. Repeated unqualified reads fail as ambiguous rather
than returning the last observation. Legacy replay evidence fails closed.

Snapshots exclude common credential files and reject detected secrets in remaining
files; see [evidence safety](evidence-safety.md). They restore only included bytes.
These are deliberate safety changes to the original v0.1 capture/replay contract.
