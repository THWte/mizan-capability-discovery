# MIZAN Document Capability Routing Decision v1

**Status:** proposed architecture decision for review. This is a policy/contract layer, not production ingestion.

## Verified inputs

- **Docling / PR #2:** multi-format parsing (PDF/DOCX/XLSX/PPTX), born-digital layout/table extraction, explicit OCR-off routing; Arabic scanned OCR remains below threshold (`scanned_arabic_table WER=1.524`) and Windows native stability remains unresolved.
- **PaddleOCR / PR #5:** materially stronger measured Arabic OCR on the shared scanned table fixture (`WER=0.667`), but OCR is always-on, DOCX/XLSX/PPTX are unsupported, base pipeline does not reconstruct table structure, Windows sequential stability is unresolved, and concurrent `.convert()` is confirmed unsafe.

Both remain **sandbox capability candidates**, not production authorities.

## Decision

Source Artifact -> Document Identity/classification -> MIZAN Capability Router -> provider candidate -> Raw Observation(s) -> future Evidence Resolution.

Routing policy:
- born-digital PDF -> Docling candidate
- DOCX/XLSX/PPTX -> Docling candidate
- scanned Arabic PDF/image -> PaddleOCR candidate
- ambiguous Arabic PDF -> Docling classification plus optional PaddleOCR comparison
- scanned table requiring row/column reconstruction -> REVIEW_REQUIRED

## Non-negotiable boundaries

1. Routing output is a candidate execution decision, never Evidence, Fact, or Accepted Fact.
2. Production approval is structurally forbidden in routing v1.
3. PaddleOCR execution must be serialized/process-isolated; concurrent `.convert()` is not permitted.
4. Scanned-table structure is not considered solved by either current sandbox.
5. Engine disagreement becomes an Evidence Resolution requirement, not a truth decision.
6. MIZAN Identity, Stable Locator, Provenance, and Canonical Contracts remain authoritative and engine-independent.
7. PR #2 and PR #5 remain independent sandbox branches until separately accepted/merged.

## Why CONNECT, not replacement

The measured capabilities are complementary. PaddleOCR is better at the tested Arabic OCR task; Docling is stronger for structure, text-layer routing, and multi-format ingestion. MIZAN therefore owns the router and keeps both engines replaceable.

## Next dependency

The next architectural layer is **Evidence Resolution**: compare multiple Raw Observations without silently promoting either engine output to truth.