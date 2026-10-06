# A9 Measured Retrieval Benchmark Result

**Run:** GitHub Actions 37517064431  
**Artifact:** 11437760879  
**Head:** ccdeec32854d10b3b0e4897d625d7321bbf14b5b  
**Dataset:** 5,000 deterministic synthetic vectors, 1,000 queries, dimension 32, top-k 10.

| Metric | Qdrant 1.19.1 | pgvector 0.8.6 / PostgreSQL 18 |
|---|---:|---:|
| Recall@5 | 1.0000 | 0.9996 |
| Recall@10 | 1.0000 | 0.9983 |
| MRR@10 | 1.0000 | 1.0000 |
| nDCG@10 | 1.0000 | 0.998853 |
| Citation Precision@1 | 1.0000 | 1.0000 |
| Metadata Filter Accuracy | 1.0000 | 1.0000 |
| Citation Preservation | 1.0000 | 1.0000 |
| Mean latency | 1.915 ms | 1.883 ms |
| p50 | 1.774 ms | 1.856 ms |
| p95 | 2.286 ms | 2.224 ms |
| Max | 5.278 ms | 5.151 ms |
| Resource snapshot | 96.07 MiB | 35.66 MiB |

pgvector relation+index size: 3,366,912 bytes.

## Critical validity observation

Qdrant reported `points_count=5000` but `indexed_vectors_count=0`. Therefore this run validates Qdrant retrieval correctness and payload/filter behavior at this corpus size, but **does not establish indexed HNSW performance for Qdrant**. The benchmark must be repeated at a corpus/configuration that confirms non-zero indexed vectors before making a final performance comparison.

## A9 decision

**pgvector: REUSE / EXTEND — preferred MIZAN Retrieval Fabric baseline candidate.**

Rationale:
- perfect metadata filtering and citation preservation;
- near-perfect retrieval quality;
- slightly lower measured mean/p95 latency in this run;
- substantially lower one-shot memory snapshot;
- aligns with MIZAN's structured relational case data and existing evaluation;
- does not require a second authoritative datastore.

**Qdrant: CONTINUE BENCHMARKING — not rejected.**

Rationale:
- perfect retrieval metrics in this run;
- dedicated vector capability remains strong;
- current run did not exercise its indexed-vector path (`indexed_vectors_count=0`), so a final indexed-performance decision would be premature.

## Architectural boundary

Retrieval rank, similarity, MRR, Recall, or engine choice cannot create Evidence, Fact, Verified Fact, or Accepted Fact. Retrieval only selects material for inspection. Citation IDs remain MIZAN-owned references.

## Deferred to A10 / later scale gate

Arabic/legal embedding quality, BM25/hybrid lexical retrieval, real legal Golden Dataset, and a larger Qdrant indexed-vector rerun.
