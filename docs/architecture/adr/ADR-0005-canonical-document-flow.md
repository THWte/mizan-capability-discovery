# ADR-0005: Canonical Document Flow v1

**Status:** Proposed
**Base:** main@e2099ec4793ab854234bc554a3209c33252f8119

## Decision
Compose Identity, Routing, Canonical RawObservation, Provenance, and Evidence Resolution into a single deterministic MIZAN-owned flow. External engines remain outside this contract and can only contribute through canonical observations/provenance accepted by the selected route.

## Hardening discovered during A7
A6 originally allowed equal text at different stable locators to corroborate. A7 closes that path: cross-locator observation sets become REVIEW_REQUIRED, because agreement at different source locations is not corroboration of the same evidence item.

## Consequence
MIZAN now has a coherent document-intelligence boundary ending at Evidence State, ready for a later Citation Engine and later interpretation/verification layers without making either extraction engine authoritative.