# ADR-0007: Retrieval Benchmark v1 — Qdrant vs pgvector

**Status:** Proposed
**Base:** main@22014b78fa174a09e0417ff288378767ec55d42f

## Decision

Benchmark Qdrant and pgvector under identical synthetic vectors, queries, filters, citation IDs, and ground truth before selecting a Retrieval Fabric backend.

Pinned benchmark versions:
- Qdrant v1.19.1
- pgvector v0.8.6 on PostgreSQL 18

## Required metrics

Recall@5/10, MRR@10, nDCG@10, Citation Precision@1, metadata filtering accuracy, citation preservation, and latency.

## Boundary

Retrieval rank is never Evidence Authority. The benchmark may choose a retrieval capability candidate, but cannot promote retrieved content to truth.

## Deferred

Arabic embedding quality and real legal retrieval are deferred to the Golden Dataset and embedding benchmark because mixing model quality into this engine benchmark would confound the result.
