# GitHub Capability Census for MIZAN: Structured Evaluation and Integration Roadmap

## Summary

MIZAN should not treat GitHub as a passive archive of code. It should treat GitHub as a
living capability ecosystem that can continuously strengthen the platform.

This initiative formalizes a structured process for discovering, evaluating, and
integrating open-source capabilities relevant to MIZAN's architecture: document
intelligence, knowledge graph, agent workflows, retrieval, observability, and
legal/document UX layers.

## Goal

- Build a formal capability discovery and evaluation process for MIZAN
- Evaluate projects across strategic technical domains
- Decide whether to REUSE, EXTEND, CONNECT, INSPIRE, or REJECT each project
- Ensure integration decisions are driven by architecture, security, privacy, and
  product fit, not by popularity alone

## Scope

We will evaluate capabilities across the following layers:

- Document Intelligence
- Arabic OCR
- Legal NLP
- Entity Resolution
- Knowledge Graph
- Temporal Graph
- RAG / GraphRAG
- Hybrid Search
- Agent Runtime
- Multi-Agent Systems
- Memory
- Workflow / HITL
- Observability / Evaluation
- Document and Case UX

## Initial candidate projects

- Docling
- Graphiti
- LangGraph
- Haystack 3
- Langfuse
- pgvector
- Paperless-ngx
- Microsoft GraphRAG

## Decision model

Each project will be evaluated against:

- Capability quality
- Maintenance and activity
- License
- Security posture
- Python / FastAPI compatibility
- Windows / local compatibility
- Arabic language support
- Privacy / local-first support
- Ease of integration
- Dependency footprint
- Testability
- Whether it fills a real gap or duplicates existing work

## Decision categories

- **REUSE**: Directly adopt the capability
- **EXTEND**: Strong base, needs MIZAN-specific adaptation
- **CONNECT**: Useful as integration layer or adjacent system
- **INSPIRE**: Good architecture or concept, not a direct fit
- **REJECT**: Not suitable for MIZAN constraints

## Expected output

- A MIZAN capability map across core strategic domains
- An initial shortlist of high-value projects
- A clear set of adoption decisions per project
- A prioritization roadmap for prototype and production integration
- A reusable evaluation template for future capability discovery

## Acceptance criteria

- A standard scorecard exists for each candidate project
- Each project receives a decision: REUSE / EXTEND / CONNECT / INSPIRE / REJECT
- At least one pilot integration is tested in sandbox
- Regression tests are defined before wider adoption
- All decisions are documented in a branch/PR workflow

## Initial priority

**Phase 1:**
- Langfuse
- Docling
- pgvector
- Haystack 3

**Phase 2:**
- Graphiti
- LangGraph
- Neo4j GraphRAG
- Docling Graph

**Phase 3:**
- Mem0
- Paperless-ngx
- Microsoft GraphRAG

## Notes

This effort is not about "pulling in big projects just because they are popular." It is
about understanding:
- what problem each project solves,
- what MIZAN should take from it,
- what we should reject,
- and how to sequence adoption safely.

This initiative is the formal entry point for MIZAN's GitHub capability development
program. See `templates/evaluation-template.md` for the per-project scorecard,
`evaluations/` for completed assessments, `docs/compatibility-matrix.md` for the scored
comparison, `research/arabic-ocr-legal-nlp.md` for the Arabic/legal domain scan, and
`docs/roadmap.md` for the phased integration plan.
