# Evidence safety and replay identity

## Snapshot policy

Snapshots exclude `.env`, `.env.*`, common credential files, private-key
extensions and credential directories. Their manifest records excluded paths;
restore does not reconstruct those files. Remaining bytes are checked for known
secret patterns and JSON credential fields before any snapshot object is written.
A suspected secret aborts the snapshot; safe files are preserved byte-for-byte.
Do not silently sanitize executable fixtures and call them exact replays.

The detector is defense in depth, not a vault or comprehensive secret scanner.
It can miss unknown formats and encoded/binary secrets and can flag synthetic
examples. Use minimal secret-free workspaces, inject credentials outside them,
and inspect evidence before sharing. Do not weaken the check to record live secrets.
Older snapshots are not automatically sanitized; inspect or retire them privately.

## Operation identity v2

Every recorded write requires a nonempty receipt, authoritative status and:
`operation_id`, `account_id`, `resource_id`, `credential_epoch`.
These are opaque, non-secret identifiers, not credential hashes or values.
For resource creation, the resource identity can be a preassigned request namespace;
retain the provider-created identity in the receipt.

The adapter supplies authoritative evidence; the store cannot authenticate a
provider receipt. An uncertain write without a receipt is an unresolved event,
not a recordable successful effect. Record its observation without secrets,
reconcile through a supported read/status endpoint, and never retry the mutation
merely to obtain a receipt.

Tool inputs must already use credential references. Detected secret-bearing
inputs are rejected rather than redacted into ambiguous lookup keys. Outputs
and receipts are redacted. Matching includes name, input, effect and all identity
fields. Reingesting identical evidence for an operation is idempotent; conflicting
evidence is rejected. Different operations with identical payloads stay distinct.
For repeated reads, supply identities too; otherwise ambiguous lookup fails.

Legacy tool evidence remains inspectable but cannot be used to build a new replay.
Legacy replay manifests are rejected. Do not invent identity metadata for historical
writes. All replay lookups are non-executing; the library is not a sandbox that
can stop a caller from using other network tools. Use a network-off replay process.

The file store assumes a single writer per run. It is not a concurrent ledger,
credential broker, tamper-proof audit log or timeout supervisor.
