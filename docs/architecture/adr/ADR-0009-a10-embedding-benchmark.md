# ADR-0009: A10 Measured Arabic/Legal Embedding Decision

**Status:** Accepted as baseline-candidate decision  
**Evidence:** GitHub Actions run 37518446419, artifact 11437857962.

## Decision

Select **BAAI/bge-m3** as MIZAN's preferred **synthetic-baseline embedding candidate (REUSE / EXTEND)**.

Do not label it production-approved. The benchmark used synthetic Arabic legal-style passages, not real Saudi case files.

## Evidence

On the strengthened 50-document / 32-query adversarial set:
- BGE-M3 Top-1: 0.9375; MRR: 0.96875; nDCG@5: 0.97310.
- multilingual-e5-base Top-1: 0.84375; MRR: 0.91667.
- multilingual-MPNet Top-1: 0.84375; MRR: 0.90625.
- All three reached Recall@5 = 1.0.
- BGE-M3 was slower on CPU, but materially stronger on legal contrast classes.

## Failure evidence

BGE-M3 still confused appellate outcome language in two queries. Dense similarity therefore must not be the only retrieval signal for legal outcome, negation, exact numeric, date, or identifier-sensitive retrieval.

## Architectural consequence

A11 Retrieval Fabric should use pgvector + BGE-M3 as baseline candidates while adding lexical/structured exact-match guards. Retrieval rank is never Evidence Authority and cannot create or upgrade facts.
