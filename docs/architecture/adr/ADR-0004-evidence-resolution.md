# ADR-0004: Evidence Resolution v1

**Status:** Proposed
**Base:** main@6e8ade2e2918644bc880ff96718512e0afd1f3e1

## Decision

Add a MIZAN-owned Evidence Resolution layer between RawObservation and future interpretation. The layer records agreement, conflict, unresolved state, rejection, or review requirement without producing truth.

## Rationale

A5.5 can route one document to different capability providers. Multiple engine outputs can therefore disagree. MIZAN must preserve that disagreement and route it explicitly rather than choosing an engine output as truth.

## Consequences

The system gains a deterministic conflict boundary and review signal. It still has no Fact or AcceptedFact production path; that remains intentionally deferred to interpretation and verification layers.
