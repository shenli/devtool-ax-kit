# Database task pack

This pack defines four cases. The executable pilot calibrates local SQLite
mechanics with reference operations; it does not run an agent, sign up with a
vendor or measure hosted-database AX.

| Case | Starting state and task | Independent assertions | Stop |
|---|---|---|---|
| Cold-start first use | Empty local workspace; create notes.sqlite and insert the fixture marker once | Fresh read-only connection finds exactly one matching row and no extra databases | 60 seconds or scope breach |
| Configured CRUD | Existing notes database; update the marker | Fresh readback sees one updated row, old value absent | 60 seconds |
| Ambiguous-write recovery | Commit occurred, client observed timeout, original receipt retained by evaluator | Pinned lookup is non-executing; fresh readback still finds one row | Missing receipt or identity conflict |
| Handoff and cleanup | Resource ready for another client, then explicitly disposable | Fresh client can read before cleanup; database and sidecars absent afterward | Uncertain cleanup or unknown resource |

Hosted adaptations must add supported signup/access, actual resource provisioning,
credential delivery by reference, provider-side ownership readback, TTL/claim
semantics and authoritative cleanup receipts. A local file is not proof of account
creation or ownership transfer. Do not bypass a site's access controls.

## Run calibration

```bash
python3 scripts/database_pilot.py
python3 scripts/validate_protocol.py taskpacks/databases/experiment.json
```

The pilot creates an isolated temporary task directory and runs the verifier in a
separate Python process with `-I`. The verifier source and expectations remain
outside the task directory. The reference operations are not an adversarial agent;
filesystem separation here does not establish a sandbox boundary. Real agent
trials need enforced read-only evaluator access and a separate evidence store.

The verifier checks a good and deliberately bad fixture for each mode. Missing
required state is failure; unreadable/corrupt database or evaluator errors are
unknown, never pass. Its output contains assertion evidence and exits nonzero for
failed or unknown checks. Read-only SQLite access must not create a missing DB.

The checked-in experiment is a development manifest for three synthetic lifecycle
runs. Calibration logs are returned in stdout; temporary files are deleted on exit.
Save a reviewed stdout artifact outside the evaluated agent's workspace for durable
evidence. No checked-in synthetic result is a product ranking or agent score.
