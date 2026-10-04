# MIZAN Capability Integration Roadmap

This roadmap sequences adoption so that MIZAN captures high-value, low-risk
capabilities first, reserves deep architectural bets for a second phase, and treats
strategic/research-only projects as references rather than dependencies.

## Phase 1 — Immediate value (high ROI, low risk)

| Priority | Project | Why first | First deliverable |
|---|---|---|---|
| 1 | **Langfuse** | Immediate observability/evaluation impact; answers "why did the system err and how do we measure improvement?" | Self-hosted Langfuse instrumenting one existing MIZAN agent workflow end-to-end |
| 2 | **Docling** | Immediate value for document ingestion/intake | `docling-serve` sandboxed against real (anonymized) Arabic case documents; OCR/table-extraction benchmark |
| 3 | **pgvector** | Natural upgrade path once MIZAN outgrows SQLite; enables hybrid search | Proof-of-concept migration of a data subset to PostgreSQL + pgvector with hybrid query benchmark |
| 4 | **Haystack 3** | Strong reference for retrieval/routing/memory pipelines and Approval/Guardrail hooks | Guardrail-layer proof of concept using Haystack's pre/post hook pattern |

**Exit criteria for Phase 1**: each project has a completed evaluation
(`evaluations/*.md`), a sandbox prototype, and a documented REUSE/EXTEND/CONNECT
decision with regression tests defined before any wider adoption.

## Phase 2 — Deep architectural evaluation

| Priority | Project | Why second | Key question to resolve |
|---|---|---|---|
| 5 | **Graphiti** | Closest conceptual match to MIZAN's temporal knowledge-graph vision | Does its fact-invalidation model map cleanly onto legal case timelines (appeals, amendments)? |
| 6 | **LangGraph** | Must be compared directly against MIZAN's existing Agent Runtime, not auto-adopted | Does it offer a material advantage over the current runtime in HITL, checkpointing, and operational complexity? |
| 7 | **Neo4j GraphRAG** | Potential backing store for Graphiti-style graph + vector hybrid retrieval | Does it add value beyond what Graphiti + pgvector already cover? |
| 8 | **Docling Graph** | Evaluate once Docling (Phase 1) and the knowledge-graph direction (Graphiti) are both validated | Does document-to-graph conversion integrate cleanly with the Graphiti data model? |

**Exit criteria for Phase 2**: a written architecture decision record (ADR) per
project, including the side-by-side LangGraph-vs-current-runtime comparison.

## Phase 3 — Strategic study only (reference, not dependency)

| Project | Treatment |
|---|---|
| **Mem0** | Study only — likely overlaps with Graphiti; do not integrate both |
| **Microsoft GraphRAG** | Reference only — Microsoft itself frames it as largely in maintenance mode; extract algorithmic ideas, not the dependency |
| **Paperless-ngx** | Reference only — GPL-3.0 licensing and non-embeddable application design rule out direct reuse; borrow ingestion/tagging architecture ideas |

## Cross-cutting research track (runs in parallel with all phases)

Arabic OCR, Legal NLP, Entity Resolution, and Temporal Graph validation
(`research/arabic-ocr-legal-nlp.md`) must run alongside Phase 1–2, since several exit
criteria (e.g., Docling's Arabic OCR benchmark, Graphiti's legal-timeline fit) depend
on it directly.

## Process for every integration (applies to all phases)

1. Sandbox prototype
2. Proof of concept against real (anonymized) MIZAN-like data
3. Internal evaluation using `templates/evaluation-template.md`
4. Draft branch / PR
5. Regression tests defined and passing
6. Decision documented (REUSE / EXTEND / CONNECT / INSPIRE / REJECT) and merged

## Tracking

All of this work is tracked under the GitHub issue drafted in
`docs/capability-census-issue.md`, which should be filed in MIZAN's main repository
(or in this repository until that link is established) as the formal entry point for
the capability development program.
