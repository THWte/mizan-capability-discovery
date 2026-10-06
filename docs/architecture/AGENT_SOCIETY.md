# MIZAN Agent Society v1

**Status:** Normative skeleton — governance layer, not yet wired to any
production workflow.
**Applies to:** the `agents/mizan_agents/` package and any future agent
that is added to the society.
**Precedence:** This document is subordinate to
[`ARCHITECTURAL_INVARIANTS.md`](ARCHITECTURAL_INVARIANTS.md). Every rule
below exists to enforce one or more of the ten invariants inside a
multi-agent runtime; it does not introduce new authority that the
Invariants document does not already grant.

See [`ADR-0002-agent-society-v1.md`](adr/ADR-0002-agent-society-v1.md) for
the decision record behind introducing this layer, and
[`agents/README.md`](../../agents/README.md) for the module-by-module
index.

---

## Why an Agent Society

As MIZAN accumulates more capabilities (Docling, PaddleOCR, and future
candidates — Langfuse, pgvector, etc.), the work of evaluating, gating, and
integrating each one has so far been performed by manual discipline: a
human operator issuing scoped directives, and a single coding agent
following them turn by turn. That discipline is real and has held (see the
Docling and PaddleOCR sandbox histories), but it does not scale and is not
independently checkable. The Agent Society formalizes the roles that
discipline was already playing into named, testable components with a
shared contract, so that the same checks (architecture compliance, scope
boundaries, adversarial coverage) can be run automatically and
repeatedly, not just remembered.

## The eight agents

| Agent | Responsibility | What it is explicitly NOT allowed to do |
|---|---|---|
| **Master Orchestrator** | Routes Handoffs between agents; the only agent that may mark a task complete | Cannot mark a task complete without an ACCEPTED Architecture Guardian handoff for that task — no bypass path exists |
| **Conversation Intelligence** | Classifies a user directive's intent (observation only) | Cannot approve, reject, merge, or promote anything to Fact/Accepted Fact |
| **Architecture Guardian** | Reviews a Handoff's payload against specific, named Invariant violations; issues PASS/FAIL | Cannot be skipped by the Orchestrator; cannot itself be overridden by any other agent |
| **Capability Discovery** | Records REUSE/EXTEND/CONNECT/INSPIRE/REJECT decisions | Cannot record a decision without a real, existing evidence file in this repo; never runs an engine or benchmark itself |
| **Evidence/Provenance** | Resolves an Observation's provenance chain to a SHA-256 Source Artifact | Produces only an `EvidenceRecord` — has no `status`, `to_fact()`, or `to_accepted_fact()` method; cannot promote further |
| **QA/Red-Team** | Deliberately attempts known-bad operations (fact smuggling, memory overwrite, cross-namespace write, engine-id-as-locator) and reports whether they were rejected | Does not "fix" failures itself — only reports pass/fail of each attack |
| **Git/PR Auditor** | Audits a list of changed file paths against a declared scope | Performs no real git/GitHub operation (no clone, push, merge, or PR creation) |
| **Evolution Agent** | Proposes architecture amendments as structured, pending records | Cannot edit `ARCHITECTURAL_INVARIANTS.md` or any ADR file; cannot adopt its own proposal — only a new, human-authored ADR amends the Invariants |

## The Handoff Contract (`agents/mizan_agents/handoff_contract.py`)

The single mechanism by which any agent passes work to another. A
`Handoff` validates, at construction time:

- `from_agent`/`to_agent` are known roles and are not equal to each other.
- `stage` is one of a fixed, closed set of pipeline stages.
- `payload` is a `dict` that never contains a `fact`/`accepted_fact`/
  `verified_fact`/`candidate_fact` key — this is the Handoff-layer
  enforcement of Invariant 2 (Observation ≠ Evidence ≠ Fact ≠ Accepted
  Fact). An agent cannot smuggle a promoted truth status through the
  inter-agent channel; the object simply fails to construct.
- `invariant_refs` (if present) are integers in `1..10` — the sender's
  explicit claim of which invariants this handoff was produced in
  compliance with. The Architecture Guardian is the agent that actually
  checks the claim against the payload; the Handoff Contract only checks
  the claim's shape.
- A `rejected` status always carries a `rejection_reason`.

## Governed Memory (`agents/mizan_agents/memory.py`)

A namespace-scoped, append-only store shared by every agent:

- An agent may only write keys in its own namespace (`f"{role}/..."`) or
  the shared namespace (`"shared/..."`) — one agent cannot silently
  overwrite another agent's state (e.g. Evolution Agent cannot write into
  Architecture Guardian's namespace to fake a PASS verdict).
- Writing an already-used key raises an error — memory is append-only, so
  `audit_log()` is a complete, tamper-evident history of every write, in
  order. This is the agent-memory analogue of Invariant 7 (Complete
  Reverse Traceability), applied to agent state instead of document
  extraction.
- A memory value is rejected if it contains a `fact`/`accepted_fact`/
  `verified_fact`/`candidate_fact` key — the same Invariant 2 rule the
  Handoff Contract enforces, checked again at the memory layer so
  promotion cannot be smuggled in through a second path.

## Explicit v1 scope boundary

This skeleton intentionally does **not**:

1. Call Docling, PaddleOCR, Langfuse, pgvector, or any other third-party
   engine. `evidence_provenance.py` only imports
   `contracts/mizan_contracts/provenance_v1.py` (pure stdlib, zero
   third-party dependencies).
2. Perform any real git/GitHub operation. `git_pr_auditor.py`'s `audit()`
   method takes a `tuple[str, ...]` of path strings and a declared scope —
   it never shells out, clones, or calls the GitHub API.
3. Implement MIZAN's interpretation/verification layers (Candidate Fact,
   Fact, Accepted Fact) — those remain out of scope, same as in
   `contracts/mizan_contracts/` (see `ADR-0001`).
4. Modify the Docling sandbox (`sandboxes/docling/`), the PaddleOCR
   sandbox (`sandboxes/paddleocr/`), or `contracts/mizan_contracts/`
   itself. `git_pr_auditor.py`'s `SCOPE_OWNED_PATHS` encodes exactly this
   boundary as a checkable rule rather than leaving it as an unenforced
   convention.
5. Change runtime behavior of any existing capability. This is a new,
   additive governance layer; no existing contract, sandbox, or test was
   modified to accommodate it.

## Relationship to existing work

- The Handoff Contract's Invariant-2 payload check and Governed Memory's
  matching value check are the agent-society-level enforcement of the
  same rule `contracts/mizan_contracts/canonical_v1.py` enforces at the
  document-extraction level (no `Fact`/`AcceptedFact` class or field
  exists in either module, by construction, not by convention).
- `evidence_provenance.py` is a thin wrapper around
  `contracts/mizan_contracts/provenance_v1.trace_to_source_sha256` — it
  adds no new trust and no new promotion path.
- `architecture_guardian.py` reuses
  `contracts/mizan_contracts/stable_locator_v1.is_external_engine_identifier`
  directly rather than re-implementing the banned-engine-ID pattern list,
  so the two layers cannot silently drift apart.
- `git_pr_auditor.py`'s scope boundary generalizes the manual rule the
  human operator has enforced across this project's history ("do not
  touch PR #2 while working A4") into a repeatable, testable check.

## Enforcement

- `tests/agents/` exercises every agent's real behavior, including
  adversarial/negative cases (see that directory's README).
- As with `tests/architecture/`, a test with nothing real to validate must
  `skip` with an explicit reason, never be fabricated as passing.
- Any future agent added to the society must be registered in
  `agents/mizan_agents/registry.py` and must use the Handoff Contract and
  Governed Memory for all cross-agent communication — direct method calls
  or shared mutable state between agent classes are not permitted.
