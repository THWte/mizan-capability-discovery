# Arabic OCR, Legal NLP, and Knowledge Graph Research

MIZAN's documents are not generic text: they are legal files, case memos, official
records, and cross-referenced case materials. This research scope exists because
general-purpose project popularity does not guarantee Arabic or legal-domain quality —
each candidate below must be verified against real (anonymized) MIZAN-like documents.

## A. Arabic Document Intelligence

Focus areas:
- Arabic OCR engines and document parsers
- Arabic table extraction
- Mixed-language PDFs (Arabic + English, common in legal/official filings)
- OCR that preserves legal formatting (numbered clauses, right-to-left layout, stamps)
- Document segmentation for Arabic legal documents

Research actions:
- Benchmark Docling's OCR backend specifically on Arabic legal scans (see
  `evaluations/docling.md` — this is the open question blocking a REUSE decision).
- Survey dedicated Arabic OCR projects (e.g., Tesseract with Arabic traineddata,
  EasyOCR Arabic support, Arabic-specific layout models) as fallback/complementary
  engines if Docling's Arabic accuracy is insufficient alone.
- Evaluate right-to-left layout handling explicitly, not just character recognition.

## B. Legal NLP (Arabic)

Focus areas:
- Arabic legal named-entity recognition (parties, courts, dates, case numbers,
  statutes cited)
- Contract clause extraction
- Case similarity (semantic similarity between case files)
- Legal entity matching (same person/organization referenced differently across
  documents)
- Court document / memo interpretation

Research actions:
- Survey Arabic legal NLP research and open models (academic + open-source); this
  space is less mature than English legal NLP, so expect more INSPIRE/adapt decisions
  than direct REUSE.
- Treat this as a space where MIZAN likely needs custom fine-tuning rather than a
  drop-in open-source solution — document this expectation explicitly in any roadmap
  communication.

## C. Entity Resolution

Focus areas:
- Matching entities across different document sources
- People / organizations / roles / contracts / legal identities
- Arabic personal name normalization (name order, transliteration variants, honorifics)
- Entity merging across documents over time

Research actions:
- Arabic name normalization is a known hard problem (multiple valid romanizations,
  compound names, honorific prefixes) — treat as a dedicated sub-project, not a
  side-effect of adopting Graphiti or any graph tool.
- Evaluate whether entity-resolution libraries used elsewhere (e.g., in Haystack's
  or Neo4j's ecosystem) have any Arabic-aware extensions, or whether this must be
  built in-house.

## D. Temporal Knowledge Graph

Focus areas:
- Timestamped facts and validity windows
- Case evolution over time
- Event chains
- Legal changes over time (e.g., a ruling superseding a prior one)

Research actions:
- This is directly addressed by Graphiti's design (see `evaluations/graphiti.md`);
  the research task here is validating that Graphiti's fact-invalidation model maps
  cleanly onto legal-case timelines (e.g., an appeal overturning a verdict), not
  finding alternative tools.

## E. Hybrid Search

Focus areas:
- Keyword + semantic + graph retrieval combined
- Legal case file retrieval
- Arabic document collection retrieval
- Relationship-aware search (e.g., "documents related to this party")

Research actions:
- pgvector (see `evaluations/pgvector.md`) handles the keyword+semantic combination
  well via PostgreSQL full-text search + vector similarity in one query.
- Graph-aware retrieval (the third leg) depends on the Graphiti/knowledge-graph
  decision — do not evaluate hybrid search in isolation from the graph layer.

## Research sequencing

1. **Phase 1**: Build the 15-domain funnel (leading projects, problems solved,
   relevance to MIZAN, what to extract) — this document is the first pass for the
   Arabic/legal/entity/graph/hybrid-search domains specifically.
2. **Phase 2**: For each project, produce a 1-page evaluation, a "what we take" page,
   a "what we reject" page, and an integration page — see `evaluations/` for the
   format already applied to Phase 1 candidates.
3. **Phase 3**: Build first sandbox integrations — Langfuse and Docling are highest
   priority; pgvector is medium-high priority (see `docs/roadmap.md`).
4. **Phase 4**: Test against real sample data — Arabic documents, case memos/files,
   2024/2025 case samples, and SQL/CSV/PDF documents.
5. **Phase 5**: Open a prototype branch, then a PR, for each validated integration.

## Open questions requiring dedicated investigation (not yet answered)

- Which Arabic OCR engine/model has the best accuracy on real legal scans:
  Docling's built-in OCR, Tesseract (Arabic traineddata), or a specialized model?
- Is there an existing open-source Arabic legal NER model usable as a starting point,
  or does MIZAN need to fine-tune from scratch?
- What is the best practical approach for Arabic personal-name normalization across
  documents?
- Does Graphiti's fact-invalidation temporal model actually fit legal case timelines
  (e.g., appeals, amendments, superseding rulings) without significant adaptation?

These four questions should each become their own tracked research task before Phase 2
architectural evaluation (Graphiti, LangGraph) begins in earnest.
