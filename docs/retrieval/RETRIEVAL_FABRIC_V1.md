# MIZAN Retrieval Fabric v1 — A11

A11 connects the measured A8/A9/A10 capabilities behind a MIZAN-owned retrieval boundary.

## Flow

Query → Arabic normalization → case/document scope guard → lexical signal → exact/structured legal guards → replaceable dense scorer (BGE-M3 baseline candidate) → hybrid reranking → MIZAN Citation + Stable Locator candidates → inspection.

## Provider classification

- Citation Engine / Stable Locator: **REUSE**
- pgvector: **REUSE / EXTEND baseline candidate**
- BGE-M3: **REUSE / EXTEND synthetic-baseline candidate**
- hybrid legal guard/reranker: **NEW CAPABILITY — MIZAN-owned**

## Guards

Arabic/Persian digits, exact long identifiers, numeric/amount distinctions, slash-form dates, negation, appellate reversal vs affirmance, finality language, and explicit case/document scope.

## Invariants

Retrieval != Evidence Authority. Retrieval candidates cannot carry fact status. Provider IDs cannot replace MIZAN locators. Every candidate must retain a citation id and stable span locator. Cross-case retrieval is explicit rather than implicit.

## Production boundary

A11 v1 is an architectural/runtime core and synthetic gate. Production deployment still requires a real/anonymized Saudi legal Golden Dataset and integration with the local MIZAN runtime.
