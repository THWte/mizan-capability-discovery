# MIZAN Compatibility Score Matrix

Each candidate is scored 1–10 across 12 dimensions. These are **initial estimates**
based on public repository information (README, license, activity, documented
architecture) — not yet validated by sandbox testing. Scores should be revised after
each project's sandbox prototype phase.

Dimensions:
1. Capability Quality
2. Activity / Maintenance
3. License Permissiveness
4. Security Posture
5. Python / FastAPI Compatibility
6. Windows / Local Compatibility
7. Arabic Language Support
8. Privacy / Local-First
9. Ease of Integration
10. Dependency Footprint (10 = light)
11. Testability
12. Real Gap Filled vs. Duplication (10 = fills a real gap)

| Project | 1. Capability | 2. Activity | 3. License | 4. Security | 5. Py/FastAPI | 6. Win/Local | 7. Arabic | 8. Privacy | 9. Integration Ease | 10. Dep. Footprint | 11. Testability | 12. Real Gap | **Total /120** | Decision |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Docling** | 9 | 9 | 10 | 7 | 9 | 6 | 3 (unverified) | 8 | 8 | 6 | 7 | 9 | **91** | EXTEND/CONNECT |
| **Graphiti** | 8 | 7 | 10 | 6 | 8 | 6 | 2 (N/A, backend-agnostic) | 7 | 6 | 5 | 6 | 9 | **80** | EVALUATE STRONGLY |
| **LangGraph** | 9 | 10 | 10 | 7 | 9 | 8 | 2 (N/A) | 7 | 6 | 6 | 8 | 4 (overlaps runtime) | **86** | EVALUATE |
| **Haystack 3** | 8 | 9 | 10 | 7 | 9 | 7 | 3 (depends on models) | 7 | 6 | 5 | 8 | 5 (partial overlap) | **84** | EVALUATE |
| **Langfuse** | 9 | 10 | 8 (core MIT, some gated) | 8 | 9 | 7 | 7 (input/output agnostic) | 9 | 9 | 7 | 8 | 9 | **100** | REUSE/EXTEND |
| **pgvector** | 8 | 9 | 10 | 9 | 9 | 8 | 7 (language-agnostic) | 10 | 7 | 9 | 8 | 8 | **102** | REUSE/EXTEND |
| **Neo4j GraphRAG** | 7 | 7 | 7 (mixed OSS/commercial) | 7 | 8 | 6 | 2 (N/A) | 6 | 6 | 5 | 7 | 6 | **74** | EVALUATE |
| **Docling Graph** | 6 | 5 | 10 | 7 | 8 | 6 | 2 (N/A) | 8 | 6 | 6 | 5 | 7 | **76** | EVALUATE |
| **Mem0** | 6 | 7 | 8 | 6 | 8 | 7 | 2 (N/A) | 6 | 6 | 7 | 6 | 4 (overlaps Graphiti) | **73** | STUDY ONLY |
| **Paperless-ngx** | 7 | 8 | 3 (GPL-3.0) | 7 | 6 | 7 | 2 (N/A) | 7 | 3 (not embeddable) | 4 | 6 | 3 (duplicative) | **63** | INSPIRE/CONNECT |
| **Microsoft GraphRAG** | 6 | 3 (maintenance mode) | 10 | 6 | 7 | 6 | 2 (N/A) | 6 | 4 | 5 | 5 | 4 (duplicative of Graphiti) | **64** | INSPIRE/REJECT |

## Reading the matrix

- **Highest-confidence early adoptions**: pgvector (102), Langfuse (100), Docling (91)
  — all score high on security/privacy, integration ease, and real-gap-filled.
- **Deep architectural evaluation required**: LangGraph (86) and Haystack 3 (84) score
  well technically but overlap with existing or planned MIZAN components — the gap
  they fill is partial, so the score reflects quality, not an automatic adoption
  signal.
- **Core vision candidate**: Graphiti (80) scores lower on current integration
  simplicity (new graph DB dependency) but is the closest conceptual match to MIZAN's
  temporal knowledge-graph vision — pair this table with `evaluations/graphiti.md` for
  the full reasoning.
- **Reference-only tier**: Paperless-ngx (63) and Microsoft GraphRAG (64) score lowest
  primarily due to license constraints and maintenance status, respectively — both
  remain valuable as architectural references, not dependencies.
- **Arabic language support is the single lowest-scoring dimension across the board**
  and must be closed with dedicated research (see `research/arabic-ocr-legal-nlp.md`)
  rather than assumed from general-purpose project popularity.

## Next revision trigger

Re-score a project immediately after its sandbox prototype phase (see
`docs/roadmap.md`), using real benchmark data instead of estimates — especially for
Arabic OCR/NLP quality, which cannot be reliably scored from documentation alone.
