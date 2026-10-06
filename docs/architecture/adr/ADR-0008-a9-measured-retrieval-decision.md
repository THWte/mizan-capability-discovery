# ADR-0008: A9 Measured Retrieval Decision

**Status:** Accepted for baseline candidate selection
**Evidence:** GitHub Actions run 37517064431, artifact 11437760879.

## Decision

Select **pgvector as the preferred baseline candidate for MIZAN Retrieval Fabric (REUSE / EXTEND)**, subject to A10 Arabic/legal embedding evaluation and later production-scale validation.

Keep **Qdrant as CONTINUE BENCHMARKING**, not rejected.

## Why this is not a simplistic winner declaration

At 5,000 points Qdrant returned `indexed_vectors_count=0`. Its perfect recall therefore cannot be used as proof of its indexed HNSW behavior. pgvector delivered near-perfect retrieval, perfect metadata/citation preservation, slightly lower measured mean/p95 latency, and a materially lower resource snapshot while fitting MIZAN's relational legal-data architecture.

## Invariant

Retrieval != Evidence Authority. Backend selection affects candidate retrieval only; it never changes evidence state or truth status.
