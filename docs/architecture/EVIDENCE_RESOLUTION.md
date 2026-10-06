# MIZAN Evidence Resolution Layer v1

**Status:** Proposed — A6.

## Purpose

Evidence Resolution compares and records relationships among canonical RawObservations. It does **not** decide legal or factual truth.

Official epistemic sequence remains:

Observation -> Evidence Resolution -> Evidence State -> Interpretation -> Candidate Fact -> Verification -> Accepted Fact

Only the first three stages are implemented here.

## Allowed states

- OBSERVED
- CORROBORATED
- CONFLICTED
- UNRESOLVED
- REJECTED
- REVIEW_REQUIRED

Forbidden outputs include FACT, VERIFIED_FACT, and ACCEPTED_FACT.

## Deterministic v1 behavior

- one observation -> OBSERVED
- multiple observations with identical normalized text -> CORROBORATED
- multiple observations with differing normalized text -> CONFLICTED + human review
- policy-sensitive material -> REVIEW_REQUIRED
- insufficient/low-quality material -> UNRESOLVED + human review
- explicitly unusable extraction -> REJECTED with reason code

CORROBORATED means only that independent observation records agree at the normalized-text level. It is **not verification** and does not establish truth.

## Preservation rule

Conflicting observations are retained independently with observation ID, stable locator, producer, and normalized text. Resolution never overwrites one engine output with another.

## Boundaries

This layer imports only the MIZAN Canonical RawObservation contract. It does not import Docling or PaddleOCR, does not own identity/stable locators, does not perform retrieval, and exposes no Fact/AcceptedFact conversion.

## Future work

v1 intentionally does not infer semantic equivalence, weight engines, use confidence scores as authority, or resolve legal contradictions. Those require later benchmarked capabilities and verification governance.
