# A10 Measured Arabic/Legal Embedding Result

**Run:** GitHub Actions 37518446419  
**Artifact:** 11437857962  
**Head:** bc095994549334833a766ab7586b0034ac26e5c9  
**Corpus:** 50 synthetic Arabic legal-style passages, 32 queries.

| Metric | BGE-M3 | multilingual-e5-base | multilingual-MPNet |
|---|---:|---:|---:|
| Top-1 accuracy | **0.9375** | 0.84375 | 0.84375 |
| MRR | **0.96875** | 0.91667 | 0.90625 |
| nDCG@5 | **0.97310** | 0.93356 | 0.93006 |
| Recall@3 | 0.984375 | 0.984375 | **1.0000** |
| Recall@5 | 1.0000 | 1.0000 | 1.0000 |
| Docs/sec CPU | 9.52 | 30.87 | **33.65** |
| Queries/sec CPU | 12.49 | 38.23 | **43.59** |

## Adversarial findings

BGE-M3 was strongest on negation, procedural contrast, numeric precision, identifiers, dates, and judgment-status contrast. It still failed two appeal/outcome queries, including distinguishing an appellate reversal from nearby appeal/affirmance language.

E5 and MPNet were materially faster on CPU but made more errors on negation/outcome/numeric contrasts.

## A10 decision

**BGE-M3: REUSE / EXTEND as the preferred synthetic-baseline embedding candidate.**

This is **not Production Approval**. A real/anonymized Saudi legal Golden Dataset remains mandatory.

**multilingual-e5-base: CONTINUE BENCHMARKING / fallback candidate.**

**multilingual-MPNet: CONTINUE BENCHMARKING / speed-oriented fallback candidate.**

## Required retrieval architecture implication

Dense embeddings alone are insufficient for MIZAN legal retrieval. Exact identifiers, monetary values, dates, negation, and judicial outcome language require hybrid lexical/structured guards and later reranking. Retrieval remains non-authoritative and cannot promote evidence state.

## Next gate

A11 Retrieval Fabric should combine:
- pgvector baseline from A9;
- BGE-M3 dense embeddings from A10;
- lexical/exact-field retrieval for case numbers, instrument numbers, amounts and dates;
- MIZAN-owned citation/stable locators;
- no retrieval-to-fact promotion.
