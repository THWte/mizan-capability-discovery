# MIZAN Court Integration Contract V1

**Status:** normative contract for the public MIZAN capability repository.
**Scope:** artifacts produced by MIZAN court-session steps, whether real-session
assistive work or courtroom simulation (including the 3D courtroom experience).

## 1. Epistemic boundary

The governing invariants are absolute:

```
Simulation != Evidence != Fact != Accepted Fact
```

- A **courtroom simulation** produces `SIMULATION_OUTPUT` artifacts only. Simulation
  output must never be read, stored, or presented as case fact.
- An artifact records an observation or an output together with its provenance.
  It does not certify truth.
- **ACCEPTED_FACT is not a state of any artifact in this repository.** Acceptance
  is a governed decision of the private MIZAN runtime, taken by the owner after
  verification. No pipeline, agent, benchmark, or schema may promote content
  automatically.

## 2. Delegation modes

Every court-session step runs under exactly one contractual delegation mode:

| Mode | Meaning |
|---|---|
| `MIZAN_HANDLES` | MIZAN performs the step autonomously under governance rules; every action is recorded as an artifact. |
| `TOGETHER` | MIZAN and the owner perform the step jointly; contributions are recorded as separate artifacts. |
| `OWNER_HANDLES` | The owner performs the step; MIZAN records the outcome without acting. |

The delegation mode is declared per step and is part of the artifact's required
identity, together with `artifact_id`, `session_id`, `step_index`,
`epistemic_class`, and `sha256` (see `contracts/court-session-artifact-v1/schema.json`).

## 3. Artifact discipline

- **Append-only.** Session artifacts form a chain: each artifact references
  `prior_artifact_id`. Correction happens by appending a superseding artifact,
  never by editing or deleting a previous one.
- **Provenance is mandatory.** Every artifact traces back to a source document
  locator and SHA-256 where a source exists.
- **Stable locators are owned by MIZAN.** Engine-generated identifiers never
  replace MIZAN artifact identities.
- **Fail-closed.** Content whose authority or provenance cannot be established is
  classified `UNKNOWN` and never promoted.

## 4. Cumulative construction without deletion

Cumulative construction without deletion is a core MIZAN rule: new capabilities
are added on top of existing ones; superseded material is marked superseded and
linked to its successor, not removed. This preserves auditability of every prior
state, including simulation outputs.

## 5. Public repository boundary

This contract governs the **public** repository.

- Real case files MUST NOT be committed to this repository — not in artifacts,
  fixtures, tests, benchmarks, logs, or documentation.
- Only synthetic or public test data may be used, and synthetic fixtures must not
  reproduce real parties, case numbers, identifiers, or content.
- Real case files and any material containing personal data, national IDs, IBANs,
  or client-confidential content remain in the private MIZAN runtime outside this
  repository.

## 6. Non-goals

This contract does not production-approve any engine, does not certify OCR or
extraction accuracy, and does not make simulation output admissible anywhere in
the evidence pipeline.
