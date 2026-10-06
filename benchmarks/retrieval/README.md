# A9 — Qdrant vs pgvector Retrieval Benchmark v1

This benchmark compares **retrieval-engine behavior**, not embedding-model quality.

## Pinned engines

- Qdrant server: `v1.19.1`
- pgvector: `v0.8.6`
- PostgreSQL: `18`

The benchmark uses the exact same deterministic 32-dimensional vectors, 5,000 synthetic chunks, 1,000 queries, metadata filters, ground truth, and MIZAN-like citation IDs for both engines.

## Metrics

- Recall@5
- Recall@10
- MRR@10
- nDCG@10
- Citation Precision@1
- metadata filtering accuracy
- citation payload preservation accuracy
- latency mean / p50 / p95 / max
- pgvector table+index bytes
- Qdrant collection counts/status (Qdrant REST does not expose a directly comparable total byte count here)
- one container resource snapshot from GitHub Actions

## Architectural boundary

Retrieval answers only **what should be inspected**. A high retrieval score does not create Evidence, Fact, Verified Fact, or Accepted Fact. Returned citation IDs remain references into the MIZAN Citation Engine.

## Not measured in v1

- Arabic embedding quality
- lexical/BM25 hybrid retrieval
- legal answer quality
- evidence authority
- a real MIZAN Golden Dataset

Those require A10 / Golden Dataset work. This v1 intentionally isolates storage/retrieval behavior before model quality is introduced.


Benchmark execution trigger: run-2026-10-06-01.
