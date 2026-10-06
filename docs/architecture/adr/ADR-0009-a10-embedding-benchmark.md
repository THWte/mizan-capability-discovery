# ADR-0009: A10 Arabic/Legal Embedding Benchmark v1

**Status:** Proposed
**Base:** main@e6628d2b7b6c01c6cb87714367689adc5e18caf8

## Decision

Benchmark three open local multilingual embedding candidates on one synthetic Arabic legal-style corpus before selecting the default MIZAN embedding provider.

The benchmark isolates embedding retrieval quality from the A9 vector-store decision by ranking in memory over the same document set.

## Candidates

- intfloat/multilingual-e5-base
- BAAI/bge-m3
- sentence-transformers/paraphrase-multilingual-mpnet-base-v2

## Boundary

Synthetic benchmark success is not production approval. Real/anonymized Golden Dataset validation remains a mandatory later gate. Embeddings cannot create evidence authority or truth.
