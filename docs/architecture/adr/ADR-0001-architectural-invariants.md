# ADR-0001: Establish MIZAN Architectural Invariants

**Status:** Accepted
**Date:** 2026-10-04
**Deciders:** MIZAN architecture (via Capability Discovery initiative)
**Related:** [`../ARCHITECTURAL_INVARIANTS.md`](../ARCHITECTURAL_INVARIANTS.md),
[`../../../sandboxes/docling/COMPARISON_AND_DECISION.md`](../../../sandboxes/docling/COMPARISON_AND_DECISION.md)

## Context

The Capability Discovery initiative is evaluating and sandbox-testing
multiple third-party engines (Docling, and candidates such as PaddleOCR and
MinerU still to be evaluated) as potential Document Intelligence / Universal
Intake components for MIZAN. The Docling sandbox prototype
(`sandboxes/docling/`) surfaced concrete evidence of a risk this initiative
must guard against structurally, not just case-by-case:

- Docling's own object model, default configuration, and native behavior
  (e.g. defaulting OCR language to Chinese, silently mis-handling Arabic)
  could easily leak into MIZAN's core contracts if not deliberately kept
  behind an adapter boundary.
- The sandbox's own comparison document initially asserted "Nothing in this
  sandbox overlaps with MIZAN's case-management, workflow, or agent-runtime
  layers" without having actually examined MIZAN's existing ingestion
  implementation — a claim that was later withdrawn and replaced with
  `NEEDS COMPARISON WITH CURRENT MIZAN INGESTION`.
- Multiple additional engine candidates are queued for evaluation (Langfuse,
  pgvector, Haystack 3, Graphiti, LangGraph, PaddleOCR, MinerU). Without a
  fixed set of invariants established *before* those evaluations proceed,
  each evaluation risks re-deriving its own ad hoc notion of identity,
  provenance, and evidence authority — leading to inconsistent contracts
  across engines and, eventually, an architecture shaped by whichever engine
  was integrated first or most enthusiastically.

MIZAN's domain (Arabic legal document intelligence) has a hard requirement
that extracted/observed content must never be silently treated as accepted,
verified fact. This requirement needs to be a structural constraint on every
future integration, not a convention that each sandbox re-invents.

## Decision

We adopt the 10 architectural invariants documented in
[`ARCHITECTURAL_INVARIANTS.md`](../ARCHITECTURAL_INVARIANTS.md) as **normative
constraints**, not recommendations:

1. MIZAN Contract Before Engine
2. Observation ≠ Evidence ≠ Fact ≠ Accepted Fact
3. MIZAN Owns Identity and Stable Locators
4. Retrieval ≠ Evidence Authority
5. Document Identity ≠ File Identity
6. Evidence Resolution Does Not Create Truth
7. Complete Reverse Traceability
8. Reproducibility Before Optimization
9. Capability First, Technology Second
10. No Engine Becomes the System

These invariants apply to every current and future engine integration,
including the already-sandboxed Docling prototype, which must be
re-evaluated against them (tracked as a follow-up Gate re-evaluation, not
performed by this ADR).

We additionally decide to:

- Establish a `contracts/` directory with versioned placeholders for the
  concrete contracts that implement these invariants:
  `canonical-contract-v1/`, `provenance-contract-v1/`,
  `identity-contract-v1/`, `stable-locator-contract-v1/`. These are created
  as skeletons in this change; their concrete schemas are follow-up work.
- Establish `tests/architecture/` as the home for architecture-level
  validation tests (currently placeholders) that will eventually make these
  invariants mechanically checkable rather than only documentation-level
  constraints.

## Consequences

### Positive

- Future engine evaluations (PaddleOCR, MinerU, Langfuse, pgvector, Haystack
  3, Graphiti, LangGraph) have a fixed, shared set of constraints to be
  checked against, rather than each evaluation inventing its own notion of
  identity/provenance/evidence authority.
- The Docling sandbox's own hard-won findings (adapter isolation, raw vs.
  normalized text separation, the 6-stage SOURCE→...→ACCEPTED FACT pipeline)
  are generalized into reusable architectural law instead of staying
  Docling-specific tribal knowledge.
- Prevents any single popular engine from becoming architecturally
  load-bearing by construction (Invariant 10), which directly mitigates the
  "what happens if the project stops being maintained" risk already flagged
  in the Docling comparison document.

### Negative / costs

- Every future engine integration now carries mandatory adapter-boundary and
  contract-compliance overhead, even when an engine's native output would be
  easy to use directly. This is an intentional, accepted cost.
- A Gate re-evaluation of the already-completed Docling sandbox against
  these invariants is now required before that sandbox's `EXTEND` decision
  can be considered final at the architecture level.

### Follow-up work (not performed by this ADR)

Per the established capability-discovery sequencing:

1. `ARCHITECTURAL_INVARIANTS.md` (this change).
2. `contracts/canonical-contract-v1/` — concrete schema.
3. `contracts/provenance-contract-v1/` — concrete schema.
4. `contracts/identity-contract-v1/` + `contracts/stable-locator-contract-v1/`
   — concrete schemas.
5. Docling Gate re-evaluation against these invariants.
6. PaddleOCR Gate evaluation.
7. MinerU Gate evaluation.

This ADR intentionally stops after step 1. No runtime behavior, no engine
integration, and no existing sandbox code is modified by this change.

## Compliance

Any implementation, sandbox, or PR that violates one of the 10 invariants
above is non-compliant with this ADR and must either be revised or must
include an explicit, reviewed amendment ADR that supersedes the relevant
invariant — invariants are not to be silently bypassed.
