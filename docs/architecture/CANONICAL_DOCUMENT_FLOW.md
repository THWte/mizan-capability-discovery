# MIZAN Canonical Document Flow v1

**Status:** Proposed — A7.

## Purpose
Bind the already-approved MIZAN components into one engine-independent operational contract:

`Source Artifact -> Document Identity -> Capability Routing -> Canonical RawObservation + Provenance -> Evidence Resolution`

The flow stops there. Interpretation, Candidate Fact, Verification, Accepted Fact, Retrieval, and Citation are not implemented by A7.

## Guarantees
- Source bytes are anchored by SHA-256 and cross-checked between Identity, Provenance, and SourceArtifactRecord.
- A DocumentIdentity must explicitly reference the source artifact.
- Every RawObservation stable locator must equal its ProvenanceRecord stable locator.
- Observation producer must equal the provenance engine.
- Only engines permitted by the MIZAN route may contribute observations.
- Multiple observations can corroborate only when they refer to the same MIZAN stable locator and come from distinct producers.
- Conflicts are retained; no winner is selected.
- Route REVIEW_REQUIRED remains review-required even if observed texts agree.
- No provider or fact receives production approval from this flow.

## Current limitation
A7 validates and composes canonical outputs but does not execute Docling or PaddleOCR. Their sandbox adapters remain separate in PR #2 and PR #5.