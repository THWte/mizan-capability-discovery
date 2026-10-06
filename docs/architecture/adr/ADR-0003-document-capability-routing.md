# ADR-0003: MIZAN Document Capability Routing v1

**Status:** Proposed
**Date:** 2026-10-06
**Base:** main@2add9ce43b7327c150e41d96d0208f755845dc15

## Context

PR #2 (Docling) and PR #5 (PaddleOCR) established complementary measured capabilities. Neither is production-approved. Agent Society v1.2 is merged, so routing is expressed as a MIZAN-owned deterministic policy rather than engine selection by convention.

## Decision

Introduce a policy-only Document Capability Router. It does not execute engines and does not import either sandbox. It maps a classified document profile to a candidate provider, optional comparison provider, constraints, and unresolved risks.

- born-digital / Office formats -> Docling candidate
- scanned Arabic/image OCR -> PaddleOCR candidate with serialized/process-isolated execution
- ambiguous Arabic PDF -> review/comparison path
- scanned-table structure -> unresolved/review-required

A route never means production approval and never means evidentiary authority.

## Consequences

Positive: engine replacement remains possible; routing rationale is explicit/testable; measured strengths are reused without making either project the system.

Negative/open: document classification still needs runtime integration; Windows native stability remains unresolved for both candidates; scanned table structure is not solved; Evidence Resolution does not yet exist.

## Invariant alignment

- Invariant 1: MIZAN policy before engine.
- Invariant 2: route/observation does not become fact.
- Invariant 3: no engine-owned identity/locator.
- Invariant 4: routing/retrieval has no evidence authority.
- Invariant 8: deterministic reason codes.
- Invariants 9/10: capability-first; no engine becomes the system.