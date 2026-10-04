# Docling vs. MIZAN Needs — Comparison and Final Decision

This document compares Docling's *measured* (not assumed) behavior against
MIZAN's requirements, based on the sandbox prototype in this folder and the
results in `benchmark/RESULTS.md`. It supersedes the preliminary assessment in
`../../evaluations/docling.md` with real evidence; that file's REUSE/EXTEND
framing is directionally confirmed but refined here.

## What Docling adds

- A working, modular pipeline for PDF/DOCX/XLSX/PPTX ingestion with layout,
  table, and OCR extraction, verified end-to-end on all tested formats.
- Table extraction that is accurate on the tested fixtures (all cells
  recovered correctly in both PDF and DOCX tables).
- Clean failure handling: malformed and unsupported files fail with a
  catchable, structured error rather than crashing the process.
- Deterministic output across repeated runs on the same input (no observed
  run-to-run drift in this test).
- A FastAPI-compatible, Python-native integration surface (not exercised
  directly in this sandbox, but consistent with the adapter's clean API).

## What Docling duplicates from existing MIZAN capability

- Nothing in this sandbox overlaps with MIZAN's case-management, workflow, or
  agent-runtime layers. Docling is strictly an ingestion/parsing capability;
  it does not compete with any existing MIZAN subsystem.

## What Docling does NOT solve

- **Arabic-aware NLP**: Docling extracts text; it does not perform Arabic
  legal NER, clause extraction, or entity resolution. MIZAN still owns all of
  that.
- **Text normalization**: Docling does not normalize Arabic presentation-form
  glyphs to standard Unicode. This is a required, non-optional post-processing
  step MIZAN must own (now implemented as a tested contract in this sandbox).
- **OCR accuracy on real scanned Arabic legal documents**: this sandbox only
  validated text-layer (born-digital) Arabic extraction. Scanned-document OCR
  accuracy for Arabic is **unverified** and must be tested separately before
  any production reliance on Docling's OCR path for scanned case files.
- **Performance at scale**: default configuration is unconditionally slow
  (OCR runs on every page). This is addressable via configuration
  (`do_ocr=False` for born-digital PDFs) but is not solved automatically.

## Risks

| Risk | Severity | Evidence / reasoning |
|---|---|---|
| Arabic text requiring normalization is silently skipped by a future integrator | Medium | Confirmed defect in raw output; mitigated by a regression test, but only if that test stays wired into CI |
| Scanned-document Arabic OCR accuracy is unknown | Medium-High | Not tested in this sandbox; only text-layer PDFs were validated |
| Default pipeline performance (~36s/page with OCR) does not scale to MIZAN's expected document volume | Medium | Measured directly; mitigated by disabling OCR for born-digital PDFs (~12s/page), still non-trivial on CPU |
| First-run network dependency conflicts with a strict local-first/air-gapped deployment | Medium | Confirmed: models download from modelscope.cn and Hugging Face Hub on first use |
| Observed "Windows fatal exception: access violation" in a background thread during testing | Low-Medium (unconfirmed severity) | Did not fail tests in this run; not reproduced consistently; needs monitoring, not dismissal |
| Upstream project changes direction or slows down | Low | Currently very active (~68k stars, frequent releases) — lowest-risk item in this table |

## Windows / local-first impact

- Runs successfully on Windows in this sandbox (all 18 tests passed on
  Windows/CPU).
- Not local-first by default: requires one-time internet access to download
  OCR/layout models. A genuinely air-gapped MIZAN deployment must vendor these
  model weights during build, not assume runtime internet access.

## Privacy impact

- No data leaves the machine during document conversion itself — only the
  one-time model download touches the network, and that fetches model
  weights, not document content.
- Self-hostable and controllable; compatible with a privacy-sensitive
  deployment once models are pre-provisioned.

## Dependency footprint

- Heavier than the README summary suggested before this sandbox: pulls in
  `docling-core`, `docling-ibm-models`, `docling-parse`, PyTorch (for
  RapidOCR), and Hugging Face tooling. This is a non-trivial dependency and
  disk-footprint commitment (hundreds of MB), not a lightweight library.

## Can it be isolated behind an adapter?

- **Yes, and this sandbox proves it concretely.** `adapter.py` is the only
  module that imports `docling`; the rest of the system (tests, any future
  MIZAN caller) depends only on `NormalizedDocumentResult`. If Docling were
  replaced, only `adapter.py` would need to change.

## What happens if the project stops being maintained?

- Because the integration is fully isolated behind `DoclingAdapter`, the
  blast radius of Docling being abandoned is contained to reimplementing one
  module against the same `NormalizedDocumentResult` contract. This is the
  direct benefit of the adapter-first design mandated for this prototype.

## Final decision

### Decision: **EXTEND**

Docling is not adopted as-is. It is adopted as an isolated ingestion
capability, wrapped by `DoclingAdapter`, with two mandatory MIZAN-side
extensions before any production use:

1. **Mandatory NFKC normalization** of all extracted text (proven necessary,
   not optional, by `test_arabic_text_matches_source_after_nfkc_normalization`).
2. **Explicit OCR-mode selection** per document (born-digital vs. scanned)
   rather than relying on the default pipeline, to avoid the measured ~3x
   performance penalty.

### Why not REUSE
Because real, measurable gaps exist (normalization requirement, performance
default, unverified scanned-Arabic-OCR accuracy) that require MIZAN-specific
handling before this can be treated as a drop-in capability.

### Why not CONNECT / INSPIRE / REJECT
The core capability (parsing, table extraction, structured output) worked
correctly across every tested format, including the hardest case (Arabic),
once the one documented normalization gap is closed. This is stronger than a
"reference only" (INSPIRE) or "adjacent system" (CONNECT) relationship, and
the measured results give no reason to REJECT.

## Suggested next step (not performed in this sandbox)

Before any wider adoption: benchmark Docling's **OCR path** (not just
text-layer extraction) against **scanned** Arabic documents, since this
sandbox only validated born-digital Arabic PDFs. This is the single largest
remaining open question and should be the next dedicated research task.
