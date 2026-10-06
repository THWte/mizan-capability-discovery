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
| **Master Orchestrator** | Routes Handoffs between agents; the only agent that may mark a task complete | (v1.1) Cannot mark a task complete without a digest-bound `GuardianApproval` whose `reviewed_handoff_id` resolves to a real, routed Handoff and whose stored digest still matches that handoff's *current* payload — no bypass path exists, and a bare "accepted" Handoff is no longer sufficient. (v1.2) Additionally cannot trust a caller-supplied `GuardianApproval`'s fields in isolation — it must resolve to a matching record in the `GuardianApprovalRegistry`, i.e. an approval the registry itself minted by actually re-running the review |
| **Conversation Intelligence** | Classifies a user directive's `intent` and (v1.1) `claim_type` (USER_DIRECTIVE/REPORTED_STATE/QUESTION/PROPOSAL/CORRECTION) | Cannot approve, reject, merge, or promote anything to Fact/Accepted Fact; a `REPORTED_STATE`/`CORRECTION` claim is structurally forced to carry `verification_required=true` |
| **Architecture Guardian** | Reviews a Handoff's payload against specific, named Invariant violations; issues PASS/FAIL with explicit `checked_invariants`/`unchecked_invariants` and (v1.1) issues a digest-bound `GuardianApproval` via `approve()` | Cannot be skipped by the Orchestrator; cannot itself be overridden by any other agent; cannot claim `coverage=FULL` while any invariant is unchecked. (v1.2) `approve()` no longer constructs a `GuardianApproval` itself — it only delegates to the `GuardianApprovalRegistry`, the sole component that mints a trusted approval, always by actually re-running the review live |
| **Capability Discovery** | Records REUSE/EXTEND/CONNECT/INSPIRE/REJECT/(v1.1)CONTINUE_BENCHMARKING decisions, plus a (v1.1) `lifecycle_status` (DISCOVERED→EVALUATED→CANDIDATE→APPROVED/REJECTED) | Cannot record a decision without a real, existing evidence file in this repo; never runs an engine or benchmark itself; cannot reach `lifecycle_status=APPROVED` without a non-empty `human_approval_reference` |
| **Evidence/Provenance** | Resolves an Observation's provenance chain to a SHA-256 Source Artifact | Produces only an `EvidenceRecord` — has no `status`, `to_fact()`, or `to_accepted_fact()` method; cannot promote further |
| **QA/Red-Team** | Deliberately attempts known-bad operations (fact smuggling, memory overwrite, cross-namespace write, engine-id-as-locator) and reports whether they were rejected | Does not "fix" failures itself — only reports pass/fail of each attack |
| **Git/PR Auditor** | Audits a list of changed file paths against a declared scope | Performs no real git/GitHub operation (no clone, push, merge, or PR creation) |
| **Evolution Agent** | Proposes architecture amendments as structured, pending records | Cannot edit `ARCHITECTURAL_INVARIANTS.md`, any ADR file, Core Contracts, agent authority, or memory governance ACLs (v1.1 `PROTECTED_TARGETS`); cannot adopt its own proposal — `requires_new_adr` is structurally fixed `true`, and only a new, human-authored ADR amends the Invariants |

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

---

## Amendment v1.1 — Hardening and the two-layer runtime distinction

**Status:** Amendment, not a silent rewrite of the v1 decision above. The
v1 skeleton described everything above this line; this section documents
what the v1.1 hardening pass added and, importantly, the relationship
between two things that must not be conflated:

1. **The Python Governance Core** (`agents/mizan_agents/`) — the
   deterministic, testable rules described in this document: the Handoff
   Contract, Governed Memory, Architecture Guardian's invariant checks,
   `GuardianApproval` digest-binding, and so on. This is what the
   `tests/agents/` suite actually exercises, and what this document is
   normative about.
2. **The GitHub Custom Agent Runtime** (`.github/agents/*.agent.md`) —
   eight Markdown agent profiles (`mizan-master`,
   `conversation-intelligence`, `architecture-guardian`,
   `capability-discovery`, `evidence-provenance`, `qa-redteam`,
   `git-pr-auditor`, `evolution`) that let a human invoke each role as a
   distinct GitHub Copilot custom agent, with role-appropriate tool
   permissions (e.g. Architecture Guardian and Evolution Agent profiles
   deliberately omit the `edit` tool so they cannot self-approve or
   self-adopt). These profiles are **delegation surfaces and instruction
   sets** for a human- or Copilot-driven session; they do not themselves
   execute the Python Governance Core's logic, and the Core does not
   depend on them. There is currently no official local validator that
   confirms these profiles against GitHub's live custom-agent schema —
   `tests/agents/test_github_agent_profiles.py` performs only an offline,
   structural check (file presence, frontmatter shape, known tool
   aliases, required section headings) and does not claim to be an
   official conformance test.

Conceptual data flow:

```
GitHub Agent Profile (.github/agents/*.agent.md)
        │  (human/Copilot invokes a named role)
        ▼
Agent Instructions / Delegation (ROLE, READ-FIRST, SOURCE OF TRUTH, ...)
        │  (agent reasons, then calls into or mirrors)
        ▼
MIZAN Governance Core (agents/mizan_agents/*.py)
        │  (Handoff Contract, Governed Memory, Guardian, Orchestrator)
        ▼
Handoff / Memory / Guardian Approval / Audit (tested, deterministic)
```

### Other v1.1 changes to the Governance Core (summary; see module
docstrings for full detail)

- **Recursive epistemic validation** (`epistemic.py`): the
  forbidden-promoted-fact-key check now walks dicts/lists/tuples at any
  nesting depth, closing the v1 gap where a nested `accepted_fact` could
  slip past a top-level-only check, at both the Handoff Contract and
  Governed Memory layers.
- **Tamper-resistant `GuardianApproval`** (`guardian_approval.py`,
  `canonical_digest.py`): a `GuardianApproval` is bound to a specific
  reviewed Handoff via a canonical SHA-256 payload digest.
  `MasterOrchestrator.complete()` now requires this object and
  independently re-derives the digest from the live, routed Handoff at
  completion time — catching forged approvals, cross-handoff relabeling,
  and mutate-after-review (TOCTOU) attacks. See
  `tests/agents/test_hardening_v1_1.py` for the full adversarial
  catalogue (cases A–L).
- **Guardian coverage honesty**: `GuardianVerdict.coverage` is always
  `"PARTIAL"` in v1, with explicit `checked_invariants`/
  `unchecked_invariants` and a `scoped_label` property
  (`CHECKED_PASS`/`CHECKED_FAIL`/`PARTIAL_PASS`) so a scoped PASS can
  never be read as full-architecture certification.
- **Governed Memory ACL**: `SHARED_PRIVILEGED_PREFIXES` restricts
  `shared/architecture_approval/*` and `shared/verified/*` to
  Architecture Guardian only, even though they live under the otherwise-
  open `shared/` namespace.
- **Conversation Intelligence claim typing**: `claim_type`
  (`USER_DIRECTIVE`/`REPORTED_STATE`/`QUESTION`/`PROPOSAL`/`CORRECTION`)
  and `verification_required` make "a reported state is not a verified
  fact" machine-checkable instead of merely a convention — e.g. "PR #7
  مدموج" classifies as `REPORTED_STATE` with `verification_required=true`,
  never auto-upgraded.
- **Capability Discovery lifecycle axis**: `lifecycle_status`
  (`DISCOVERED`→`EVALUATED`→`CANDIDATE`→`APPROVED`/`REJECTED`) is
  orthogonal to the existing `decision` field; reaching `APPROVED`
  structurally requires a non-empty `human_approval_reference` (mirrors
  the PaddleOCR precedent: sandbox `CONNECT` decision ≠ production
  approval).
- **Evolution Agent protected targets**: `PROTECTED_TARGETS` and a
  structurally-fixed `requires_new_adr=true` field make explicit that no
  proposal can ever exempt itself from human ADR review for the
  Invariants document, ADRs, Core Contracts, agent authority, or memory
  governance.

No change in this amendment modifies `contracts/mizan_contracts/`,
`docs/architecture/ARCHITECTURAL_INVARIANTS.md`, or anything in
`sandboxes/docling/` (PR #2) or `sandboxes/paddleocr/` (PR #5).

---

## Amendment v1.2 — Approval Authenticity (Guardian Approval Registry)

**Status:** Amendment to v1.1, not a replacement of it. v1.1's digest
binding closed "forge a Handoff" and "mutate the payload after review"
(TOCTOU). It left one gap open: `canonical_digest()` is a pure, public
function, not a secret. A caller able to read a routed Handoff's payload
could compute its digest themselves and hand-construct a *structurally
valid* `GuardianApproval` whose fields — `task_id`, `reviewed_handoff_id`,
`reviewed_payload_digest`, `issued_by`, `verdict="PASS"` — happen to match
that real Handoff, without ever calling
`ArchitectureGuardianAgent.review()`/`approve()`. Every v1.1 check
(task/handoff agreement, live digest re-check, verdict) passes for such a
forgery, because it is checking "does this approval's shape match a real
Handoff", not "was this approval ever actually produced by a real
review".

**This is not a cryptography problem.** The hardening directive for this
amendment is explicit: no signatures, secrets, or tokens were added —
Python has no true access control, and a secret with no trust root to
anchor to would be security theater, not a real fix (the same point
`guardian_approval.py`'s v1.1 docstring already makes). The actual fix is
**structural**: a trusted `GuardianApproval` can now only ever be *minted*
by a new component, `GuardianApprovalRegistry`
(`agents/mizan_agents/approval_registry.py`), whose single write path,
`register_from_guardian(handoff, *, approval_id, issued_at)`:

1. requires a real `Handoff` object as input — never a pre-built verdict
   or approval (rejects any non-`Handoff` input outright);
2. always, unconditionally, re-runs the real review logic
   (`run_guardian_review`, extracted from
   `ArchitectureGuardianAgent.review` as a module-level free function so
   the registry can call it directly) against that exact `Handoff`,
   live, right now;
3. independently recomputes the canonical digest from that same
   `Handoff`'s current payload;
4. only then constructs and stores the resulting `GuardianApproval`.

There is **no parameter anywhere** on this write path through which a
caller can hand over an already-decided outcome. `ArchitectureGuardianAgent`
no longer constructs a `GuardianApproval` itself at all — its `approve()`
method is now a thin, named entry point that delegates entirely to
`approval_registry.register_from_guardian(...)`.

### The authority check this amendment adds to completion

`MasterOrchestrator.complete(task_id, approval)` no longer trusts the
caller-supplied `approval` object's fields in isolation. It now calls
`self._approval_registry.validate(approval)` first, which:

- raises `AgentContractError` if `approval.approval_id` was never issued
  through `register_from_guardian` (a forged-from-scratch approval, no
  matter how well-formed, is never found — this is what closes M1/M3);
- raises `AgentContractError` if any field on the supplied `approval`
  (task_id, reviewed_handoff_id, digest, verdict, coverage,
  checked/violated invariants) differs from the registry's own stored
  record for that `approval_id` (verdict-tampering / relabeling onto a
  different task or handoff — M2/M4/M5);
- otherwise returns the registry's own trusted record, which is then used
  for every subsequent check (`_find_routed_handoff`, live digest
  re-check, `permits_completion`) in place of the caller-supplied object.

The `approval.task_id != task_id` check on the raw, caller-supplied object
remains the very first line of `complete()`, preserved deliberately so
that passing `approval=None` still fails loudly with `AttributeError` (an
existing, intentional behavior from v1.1), before `validate()`'s
`isinstance` check would otherwise turn that into an `AgentContractError`.

### Coverage semantics made explicit in code (not only prose)

`approval_registry.py` defines `ARCHITECTURE_GATE_V1`,
`FULL_ARCHITECTURE_CERTIFICATION`, and `COMPLETION_SCOPE =
ARCHITECTURE_GATE_V1` as plain constants, so that no code path can claim
the narrow, PARTIAL-coverage gate this registry vouches for is the same
thing as full architecture certification. `GuardianVerdict.scoped_label`
(`PARTIAL_PASS` vs `CHECKED_PASS`/`CHECKED_FAIL`, from v1.1) remains the
human-facing expression of the same rule; this amendment adds a
machine-checkable constant pair so the distinction cannot silently drift.

### Replay policy (explicit, documented, tested)

`GuardianApprovalRegistry.mark_consumed(approval_id, task_id)` records
`(approval_id, task_id)` pairs. Replaying the *same* approval to
re-complete the *same* task it already completed is an idempotent no-op —
`complete()` does not raise, matching `is_complete()`'s existing
set-membership idempotency. Replaying the same `approval_id` against a
*different* task is already rejected earlier, by the task_id field
comparison inside `validate()` (or the first-line check in `complete()`),
before `mark_consumed` is ever reached — so cross-task replay is
rejected, same-task replay is a harmless no-op, and neither is left as
undefined behavior.

### Honest limitation (M8)

Python offers no true access control. Nothing stops code that imports
`approval_registry.py` from calling `register_from_guardian` directly,
bypassing `ArchitectureGuardianAgent.approve()` as a named entry point.
This amendment does not claim otherwise. What it does claim, and what is
tested, is narrower and still real: that direct call still only ever
produces a record by *actually re-running the real review* against
whatever `Handoff` is supplied — there is no parameter for injecting a
pre-decided verdict, and no public setter anywhere on the registry that
stores an arbitrary record without going through live review (see
`test_m8_register_from_guardian_rejects_non_handoff_input` and
`test_registry_has_no_public_setter_besides_register_from_guardian` in
`tests/agents/test_hardening_v1_2.py`).

### Adversarial coverage (M1–M10)

See `tests/agents/test_hardening_v1_2.py` for the full, explicitly
labeled catalogue: forged-approval-with-correct-digest (M1),
verdict-tampering on a reused real `approval_id` (M2), never-registered
but well-formed approval (M3), cross-task relabeling (M4), cross-handoff
relabeling (M5), the real-approval control case that must still succeed
(M6), duplicate `approval_id` rejection at registration (M7), direct
registry-write-bypass honesty (M8), PARTIAL-cannot-become-FULL (M9), and
replay policy (M10).

No change in this amendment modifies `contracts/mizan_contracts/`,
`docs/architecture/ARCHITECTURAL_INVARIANTS.md`, or anything in
`sandboxes/docling/` (PR #2) or `sandboxes/paddleocr/` (PR #5).

