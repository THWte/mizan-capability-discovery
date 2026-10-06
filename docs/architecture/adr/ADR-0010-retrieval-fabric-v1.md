# ADR-0010 — MIZAN Retrieval Fabric v1

**Status:** Proposed for A11

CONNECT A8 Citation Engine, A9 pgvector baseline candidate, and A10 BGE-M3 synthetic-baseline candidate behind a MIZAN-owned hybrid Retrieval Fabric.

Dense retrieval is a recall signal, never authority. Exact identifiers, numbers, dates and legally decisive contrast language receive deterministic structured signals. Case/document scope is enforced before ranking.

Provider decisions: pgvector REUSE/EXTEND; BGE-M3 REUSE/EXTEND synthetic candidate; structured legal guard NEW CAPABILITY; Citation/Stable Locator REUSE.

Retrieval output is material for inspection only. It cannot create Evidence, Fact, Verified Fact, or Accepted Fact.
