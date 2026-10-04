# MIZAN Capability Discovery

MIZAN GitHub Capability Census: a structured process for discovering, evaluating, and
integrating open-source capabilities into MIZAN — treating GitHub as a living
capability ecosystem rather than a passive code archive.

## Why this exists

MIZAN should not adopt a project just because it is popular. Each candidate is
evaluated for the specific gap it fills in MIZAN's architecture (document
intelligence, knowledge graph, retrieval, agent runtime, observability, legal/Arabic
domain fit), then given one decision: **REUSE / EXTEND / CONNECT / INSPIRE / REJECT**.

## Structure

| Path | Purpose |
|---|---|
| [`docs/capability-census-issue.md`](docs/capability-census-issue.md) | The formal initiative write-up (goal, scope, decision model, acceptance criteria) |
| [`templates/evaluation-template.md`](templates/evaluation-template.md) | Standard per-project evaluation template |
| [`evaluations/`](evaluations/) | Completed evaluations for each candidate project |
| [`docs/compatibility-matrix.md`](docs/compatibility-matrix.md) | MIZAN Compatibility Score matrix (scored 1–10 across 12 dimensions) |
| [`research/arabic-ocr-legal-nlp.md`](research/arabic-ocr-legal-nlp.md) | Arabic OCR, Legal NLP, Entity Resolution, and Temporal Graph domain research |
| [`docs/roadmap.md`](docs/roadmap.md) | Phased integration roadmap (Phase 1–3) |

## Phase 1 candidates (highest priority)

- [Langfuse](evaluations/langfuse.md) — observability & evaluation — **REUSE/EXTEND**
- [Docling](evaluations/docling.md) — document intelligence — **EXTEND/CONNECT**
- [pgvector](evaluations/pgvector.md) — hybrid semantic search — **REUSE/EXTEND**
- [Haystack 3](evaluations/haystack3.md) — RAG/guardrail patterns — **EVALUATE**

## Phase 2 candidates (deep architectural evaluation)

- [Graphiti](evaluations/graphiti.md) — temporal knowledge graph — **EVALUATE STRONGLY**
- [LangGraph](evaluations/langgraph.md) — agent runtime comparison — **EVALUATE**

## Phase 3 (reference only)

- [Paperless-ngx](evaluations/paperless-ngx.md) — **INSPIRE/CONNECT**
- [Microsoft GraphRAG](evaluations/microsoft-graphrag.md) — **INSPIRE/REJECT**

See [`docs/roadmap.md`](docs/roadmap.md) for the full sequencing and exit criteria.
