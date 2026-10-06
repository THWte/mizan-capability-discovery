# ADR-0002: Introduce MIZAN Agent Society v1

**Status:** Accepted
**Date:** 2026-10-06
**Deciders:** MIZAN architecture (via Capability Discovery initiative)
**Related:** [`../ARCHITECTURAL_INVARIANTS.md`](../ARCHITECTURAL_INVARIANTS.md),
[`../adr/ADR-0001-architectural-invariants.md`](ADR-0001-architectural-invariants.md),
[`../AGENT_SOCIETY.md`](../AGENT_SOCIETY.md),
[`../../../sandboxes/docling/`](../../../sandboxes/docling/),
[`../../../sandboxes/paddleocr/`](../../../sandboxes/paddleocr/)

## Context

Two capability-evaluation cycles (Docling, PaddleOCR) have now been
completed under `ARCHITECTURAL_INVARIANTS.md` and MIZAN Core Contracts v1
(`contracts/mizan_contracts/`). Both cycles were driven end-to-end by a
human operator issuing scoped, execute-first directives to a single coding
agent, with the operator manually re-checking architecture compliance,
scope boundaries (e.g. "do not touch PR #2 while working A4"), and
adversarial coverage at every gate.

That manual discipline worked — both sandboxes were honestly gated, with
real negative findings preserved (Docling's `NEEDS COMPARISON WITH CURRENT
MIZAN INGESTION`, PaddleOCR's Windows concurrency `CONFIRMED UNSAFE`
finding) — but it does not scale past one human operator's attention, and
it is not independently re-runnable: the checks the operator performed
exist only as conversation history, not as code.

As more capability candidates queue up (Langfuse, pgvector, and others in
`docs/roadmap.md`), the roles that discipline was already playing —
routing work, gating architecture compliance, recording capability
decisions, checking evidence chains, red-teaming the system's own
guarantees, auditing changeset scope, and proposing (not adopting)
architecture amendments — need to become named, testable components.

## Decision

We introduce `agents/mizan_agents/` as a governed multi-agent runtime
**skeleton**: eight agent roles, a shared Handoff Contract, and a shared
Governed Memory store. See
[`../AGENT_SOCIETY.md`](../AGENT_SOCIETY.md) for the full role-by-role
specification.

1. **Master Orchestrator** — routes Handoffs; the only agent that may mark
   a task complete, and only after an ACCEPTED Architecture Guardian
   handoff exists for that task.
2. **Conversation Intelligence** — classifies user-directive intent
   (observation only, no approval authority).
3. **Architecture Guardian** — the only agent empowered to approve a
   Handoff against `ARCHITECTURAL_INVARIANTS.md`.
4. **Capability Discovery** — records REUSE/EXTEND/CONNECT/INSPIRE/REJECT
   decisions, each required to reference a real, already-existing evidence
   file in this repository.
5. **Evidence/Provenance** — wraps
   `contracts/mizan_contracts/provenance_v1.trace_to_source_sha256`;
   produces Evidence, never Fact.
6. **QA/Red-Team** — deliberately attempts known-bad operations (fact
   smuggling, memory overwrite, cross-namespace write, engine-id-as-
   locator) and reports whether they were actually rejected.
7. **Git/PR Auditor** — audits a changed-paths list against a declared
   scope; performs no real git/GitHub operation.
8. **Evolution Agent** — proposes architecture amendments as structured,
   pending records; cannot adopt its own proposal.

We additionally decide to:

- Enforce Invariant 2 (Observation ≠ Evidence ≠ Fact ≠ Accepted Fact) at
  **two** independent layers inside the agent society: the Handoff
  Contract (payload shape check at construction time) and Governed Memory
  (value shape check at write time) — so promotion cannot be smuggled in
  through either the inter-agent channel or the shared memory store alone.
- Make Governed Memory namespace-scoped and append-only, giving the
  society a tamper-evident audit log (`audit_log()`) as the agent-memory
  analogue of Invariant 7 (Complete Reverse Traceability).
- Keep this skeleton's scope strictly additive: zero third-party
  dependencies, zero network calls, zero real git/GitHub operations, no
  change to `contracts/mizan_contracts/`, `sandboxes/docling/`, or
  `sandboxes/paddleocr/`.

## What this ADR explicitly does NOT decide

- It does not wire any agent to a real engine (Docling, PaddleOCR,
  Langfuse, pgvector, or any other).
- It does not implement MIZAN's interpretation/verification layers
  (Candidate Fact, Fact, Accepted Fact) — those remain future work, exactly
  as scoped out by ADR-0001.
- It does not grant the Git/PR Auditor agent, or any other agent, the
  ability to perform a real git or GitHub operation. `git_pr_auditor.py`'s
  `audit()` method takes path strings and a declared scope; it never
  shells out.
- It does not change runtime behavior of any existing contract or sandbox.

## Consequences

### Positive

- The architecture-compliance and scope checks that were previously only
  performed manually by a human operator now exist as code
  (`architecture_guardian.py`, `git_pr_auditor.py`) that can be re-run
  deterministically and tested with adversarial cases
  (`tests/agents/test_qa_redteam_agent.py`,
  `tests/agents/test_agent_society_integration.py`).
- Future capability evaluations (Langfuse, pgvector, and beyond) gain a
  reusable `CapabilityDiscoveryAgent` that structurally prevents recording
  a decision without pointing at real evidence — generalizing the rule
  already applied manually to the Docling and PaddleOCR sandboxes.
- The Handoff Contract's and Governed Memory's dual enforcement of
  Invariant 2 means a future agent cannot accidentally (or deliberately)
  introduce a promotion path merely by adding a new field to a payload or
  memory value — both choke points already reject the known forbidden key
  names.

### Negative / open risk

- This is a skeleton with simulated/stubbed coordination (in-process
  Python objects, not a real multi-process or multi-session runtime). It
  does not yet prove the society works across real, separate coding-agent
  sessions the way the Docling/PaddleOCR sandboxes proved real engine
  behavior. That gap is tracked as explicit future work, not hidden.
- `architecture_guardian.py`'s checks are necessarily a fixed, enumerated
  list of specific invariant violations it knows how to detect in a
  payload shape — it is not a general-purpose policy engine and will need
  extension as new violation patterns are discovered, the same way
  `tests/architecture/` already documents genuine coverage gaps rather
  than claiming completeness.

## Alternatives considered

- **Do nothing; keep relying on manual operator discipline.** Rejected:
  does not scale past one operator's attention and leaves no re-runnable
  artifact of the checks performed — exactly the gap this ADR closes.
- **Build a general-purpose agent framework (e.g. wire in LangGraph) before
  defining MIZAN's own agent contracts.** Rejected per Invariant 1 (MIZAN
  Contract Before Engine) and Invariant 9 (Capability First, Technology
  Second): MIZAN's own Handoff Contract and Governed Memory rules are
  defined first; a general-purpose framework remains a future,
  independently-gated evaluation (already queued in `docs/roadmap.md`
  Phase 2), not a prerequisite for this skeleton.

## Amendment v1.1 (2026-10-06, same PR cycle) — hardening, not a new decision

This ADR's original decision (above) stands unchanged. The v1.1 hardening
pass closed six identified vulnerabilities in the skeleton's enforcement
without altering any of the role boundaries, scope limits, or "what this
ADR explicitly does NOT decide" items listed above:

- Master Orchestrator's completion gate (#1 above) now requires a
  digest-bound `GuardianApproval`, re-verified against the live routed
  Handoff at completion time, instead of trusting any Handoff merely
  labeled `from_agent=architecture_guardian, status=accepted`.
- Invariant-2 enforcement (Handoff Contract + Governed Memory) is now
  recursive (any nesting depth), not top-level-only.
- Architecture Guardian's `coverage` field and `scoped_label` make the
  existing "fixed, enumerated list of specific invariant violations"
  limitation (already disclosed in Negative/open risk, above) explicit and
  machine-readable rather than only prose-documented.
- Governed Memory gained a privileged-namespace ACL
  (`SHARED_PRIVILEGED_PREFIXES`) so Architecture Guardian's approval
  records cannot be forged by another agent writing to the same shared
  namespace.
- Conversation Intelligence and Capability Discovery gained additional
  classification fields (`claim_type`/`verification_required`,
  `lifecycle_status`) that make existing informal rules ("a reported merge
  is not a verified merge", "a CONNECT decision is not a production
  approval") structurally enforced instead of only conventions.
- Eight `.github/agents/*.agent.md` GitHub Custom Agent profiles were
  added as a **separate runtime layer** (delegation/instruction surface),
  distinct from this ADR's Python Governance Core decision. See
  `AGENT_SOCIETY.md`'s "Amendment v1.1" section for the full
  two-layer-runtime explanation and data-flow diagram.

No change in this amendment modifies `contracts/mizan_contracts/`,
`docs/architecture/ARCHITECTURAL_INVARIANTS.md`, `sandboxes/docling/`
(PR #2), or `sandboxes/paddleocr/` (PR #5).
