# A27–A30 — Long Arabic Legal Document Intelligence v1

## Objective
Process very large Arabic legal documents without whole-document memory dependence, silent page loss, or loss of source traceability.

## Architecture
SOURCE PDF → source SHA-256 → page census → page-level quality routing → incremental page processing → checkpoint → legal spans → hierarchical sections → retrieval/citation layers.

### A27 Long Document Streaming
Pages are consumed incrementally. Completed page identities are checkpointed with an integrity hash. Resume skips completed pages and rejects a checkpoint belonging to another document/source.

### A28 Selective OCR
OCR is a page decision, never an automatic whole-document decision:
- sufficient text layer → TEXT_ONLY
- raster page → OCR_ONLY
- ambiguous mixed page → TEXT_PLUS_OCR_COMPARE
- raster/table page → TABLE_SPECIALIST
- explicit low-quality signal → HUMAN_REVIEW

This is routing policy only. Docling/PaddleOCR remain restricted and not production-approved.

### A29 Hierarchical Legal Segmentation
Page text is segmented into deterministic bounded spans with offsets, page identity and legal-section labels. Retrieval spans are derivatives; they do not replace canonical raw text and cannot become facts.

### A30 Stress Gate
CI generates 1000 synthetic pages × 1000 words/page (1,000,000 words) and requires:
- zero silent page loss
- 100% page completion traceability
- resume after completion reprocesses zero pages
- million-word target reached
- architecture/contracts regression remains green

The benchmark deliberately measures the MIZAN orchestration/segmentation layer, not real PDF decoding or OCR throughput. Real 100/500/1000-page PDF/OCR performance on Windows remains a separate local-runtime gate and must not be inferred from this synthetic benchmark.

## Non-negotiable boundaries
Observation != Evidence != Fact != Accepted Fact.
Retrieval != Evidence Authority.
Stable locators remain MIZAN-owned.
Raw source is preserved; chunks/spans are rebuildable derivatives.
No real case material is used by CI.
