# Docling vs. MIZAN Needs — Comparison and Final Decision (Revision 2)

This document compares Docling's *measured* (not assumed) behavior against
MIZAN's requirements, based on the sandbox prototype in this folder and the
results in `benchmark/RESULTS.md`. This revision corrects a false claim from
Revision 1 and incorporates new evidence: real OCR routing, a synthetic
scanned Arabic corpus with measured CER/WER, a Windows stability
investigation, separated cold/warm benchmarks, and an offline/local-first
verification.

## MIZAN's evidence pipeline — and where this sandbox sits in it

```
SOURCE -> RAW EXTRACTION -> NORMALIZATION -> INTERPRETATION -> VERIFICATION -> ACCEPTED FACT
          \_______________________________/
             this adapter's scope only
```

`DoclingAdapter` and `NormalizedDocumentResult` cover exactly the first two
stages: **RAW EXTRACTION** (`raw_text`, exactly what Docling returned) and
**NORMALIZATION** (`normalized_text`, after Unicode NFKC, computed inside the
adapter — see `benchmark/RESULTS.md` §2). Neither Docling nor this adapter
performs or is permitted to perform INTERPRETATION, VERIFICATION, or produce
an ACCEPTED FACT. Nothing returned by `DoclingAdapter.convert()` should ever
be written directly into a MIZAN fact store without passing through MIZAN's
own interpretation and verification layers, which do not exist in this
sandbox and are out of scope for it.

## What Docling adds

- A working, modular pipeline for PDF/DOCX/XLSX/PPTX ingestion with layout,
  table, and OCR extraction, verified end-to-end on all tested formats.
- Table extraction that is accurate on **born-digital** tested fixtures (all
  cells recovered correctly in both PDF and DOCX tables). OCR-path table
  extraction (scanned Arabic table) is materially worse — see
  `benchmark/RESULTS.md` §5.
- Clean failure handling: malformed and unsupported files fail with a
  catchable, structured error rather than crashing the process.
- Deterministic output across repeated runs on the same input at the
  adapter-contract level (no observed run-to-run drift in `raw_text`/
  `normalized_text`), independent of the separate native-level stability
  question in §"Risks" below.
- Configurable OCR language support (via `RapidOcrOptions(lang=...)`) that,
  once correctly configured, CAN recognize Arabic script — but does not do so
  by default (critical finding, see below).

## What Docling duplicates from existing MIZAN capability

**`NEEDS COMPARISON WITH CURRENT MIZAN INGESTION`**

Revision 1 of this document claimed "Nothing in this sandbox overlaps with
MIZAN's case-management, workflow, or agent-runtime layers." **That claim is
withdrawn: this sandbox never examined MIZAN's actual current ingestion code,
so it has no basis to assert overlap or non-overlap.** A real comparison
requires reading MIZAN's existing document-ingestion implementation (if one
exists) and comparing it feature-by-feature against Docling's measured
behavior above — this has not been done. Until that comparison exists, assume
unknown overlap, not zero overlap.

## What Docling does NOT solve

- **Arabic-aware NLP**: Docling extracts text; it does not perform Arabic
  legal NER, clause extraction, or entity resolution. MIZAN still owns all of
  that.
- **Production-quality Arabic OCR**: measured CER 36%–100%, WER 43%–152%
  across 5 synthetic scanned-Arabic cases, even after fixing the default
  Chinese-language misconfiguration (see `benchmark/RESULTS.md` §4–§5). This
  is **not usable for real scanned legal documents** in its current
  configuration without a different engine/model or substantial tuning and a
  much larger validation corpus.
- **Reliable table structure recovery under OCR**: `scanned_arabic_table`
  failed even the loose sanity ceiling (WER=1.524); Arabic table headers and
  status values were effectively lost.
- **Performance at scale without explicit routing**: the *default*
  configuration is unconditionally slow (OCR runs on every page, and in the
  wrong language for Arabic). This sandbox's own `adapter.py` OCR-routing +
  explicit `lang=["arabic","en"]` configuration is a required MIZAN-side fix,
  not something Docling provides out of the box.
- **Soak-tested Windows stability**: the access-violation investigation in
  `benchmark/RESULTS.md` §8 remains `UNRESOLVED`, not cleared.

## Risks

| Risk | Severity | Evidence / reasoning |
|---|---|---|
| Default Docling OCR config silently fails on Arabic (misreads as CJK, or silently drops Arabic while keeping English) | **High** | Directly reproduced in this sandbox; the dangerous failure mode (silent drop in mixed-language documents) is the single most important finding of this round |
| Arabic OCR quality remains poor even after fixing the language config | **High** | Measured CER/WER, not assumed; see `benchmark/RESULTS.md` §5 |
| Windows native access violation, root cause unconfirmed | **Unresolved** (explicitly not downgraded to Low) | Reproducible stack trace implicates `docling_parse`; not reliably reproducible on demand; not ruled out under production load |
| First-run network dependency conflicts with strict local-first/air-gapped deployment | Medium | Confirmed: both HF Hub and `modelscope.cn` models required; offline mode works once cached (verified), but cache must be pre-provisioned |
| Cold-start + first-conversion latency (~41–43s) may be unacceptable for short-lived/serverless invocation patterns | Medium | Measured directly, see `benchmark/RESULTS.md` §7 |
| Text requiring NFKC normalization is silently mishandled by a future integrator who bypasses this adapter | Low-Medium | Mitigated: normalization is now enforced inside the adapter itself, not opt-in |
| Upstream project changes direction or slows down | Low | Currently very active (~68k stars, frequent releases) |

## Windows / local-first impact

- Runs successfully on Windows for all format/born-digital/OCR-routing tests
  in this sandbox.
- Confirmed to work fully offline once models are cached (see
  `benchmark/RESULTS.md` §9) — this is a positive, verified finding, not an
  assumption.
- Still requires a one-time internet-connected provisioning step (or vendored
  model weights) before first use; a genuinely air-gapped MIZAN deployment
  must pre-provision the exact cache paths documented in §9.
- The Windows access-violation question (§8) remains open and specifically
  Windows-flagged by the user's original requirement; it is not resolved by
  this sandbox.

## Privacy impact

- No document content leaves the machine during conversion (verified by the
  offline test, which blocks network reachability and conversions still
  succeed/fail identically with no network calls needed for the document
  itself).
- Only model weight downloads touch the network, and only during
  provisioning, not per-document.

## Dependency footprint

- Heavier than a lightweight library: `docling-core`, `docling-ibm-models`,
  `docling-parse` (native C++ extension — see §8 risk), PyTorch, onnxruntime
  (newly required for the Arabic-language OCR model specifically), and
  Hugging Face tooling. Multiple hundred MB on disk, two different ML runtime
  backends (torch + onnxruntime) now required for full language coverage.

## Can it be isolated behind an adapter?

- **Yes, and this sandbox proves it concretely.** `adapter.py` is the only
  module that imports `docling`; the rest of the system (tests, any future
  MIZAN caller) depends only on `NormalizedDocumentResult`. If Docling were
  replaced, only `adapter.py` would need to change. The OCR-language fix in
  this revision was also entirely contained inside `adapter.py`, confirming
  the isolation holds even for significant configuration changes.

## What happens if the project stops being maintained?

- Because the integration is fully isolated behind `DoclingAdapter`, the
  blast radius of Docling being abandoned is contained to reimplementing one
  module against the same `NormalizedDocumentResult` contract.
- The native-code dependency (`docling_parse`) and the as-yet-unresolved
  access violation (§8) mean an abandoned Docling could leave MIZAN stuck on
  an unmaintained native binary with an open stability question — this is a
  stronger argument for keeping the adapter boundary strict than in Revision
  1's assessment.

## Final decision

### Decision: **EXTEND** (reaffirmed, with stronger caveats than Revision 1)

Docling is not adopted as-is, and is NOT adopted for production Arabic OCR in
its current configuration. It is adopted as an isolated, adapter-wrapped
ingestion capability for **born-digital** documents across the 5 tested
formats, with the following now-implemented, mandatory MIZAN-side extensions:

1. **Mandatory NFKC normalization** inside the adapter (implemented and
   tested, not optional).
2. **Explicit OCR routing** (born-digital/scanned/ambiguous) inside the
   adapter (implemented and tested, not optional).
3. **Explicit Arabic-language OCR configuration** (`lang=["arabic","en"]`) —
   without this, Arabic OCR silently fails. (Implemented in this revision.)

### What remains explicitly NOT extended to production readiness

- Scanned-document Arabic OCR quality (CER/WER too high for legal-document
  reliability).
- The Windows access-violation question (UNRESOLVED).
- Any claim about overlap with MIZAN's existing ingestion (NEEDS COMPARISON,
  not yet performed).

### Why not REUSE
Real, measurable, and in some cases newly-discovered-this-round gaps
(default-language OCR failure, poor Arabic OCR quality even when fixed,
unresolved native stability risk) mean this cannot be treated as a drop-in
capability for MIZAN's actual target documents (Arabic legal text, plausibly
including scanned material).

### Why not CONNECT / INSPIRE / REJECT
The born-digital path (5 formats, including Arabic text-layer PDFs once
NFKC-normalized) works correctly and is adapter-isolated — stronger than a
"reference only" (INSPIRE) or "adjacent system" (CONNECT) relationship. The
measured results are mixed, not uniformly bad, so REJECT is not supported
either — but the Arabic-OCR and Windows-stability findings are serious enough
that REUSE is not honest.

## Suggested next steps (not performed in this sandbox)

1. Compare against MIZAN's actual current document-ingestion implementation
   (if any) to resolve the "NEEDS COMPARISON" item above — this is now the
   single largest unresolved question from the original comparison
   requirements.
2. Evaluate at least one alternative Arabic OCR engine/model (e.g. Tesseract
   with Arabic traineddata, a different RapidOCR model size/backend, or a
   cloud/managed Arabic OCR service weighed against the privacy/local-first
   requirement) against the same scanned corpus and CER/WER methodology used
   here, to establish whether Docling's OCR quality gap is fixable within the
   Docling ecosystem or requires swapping the OCR engine entirely.
3. Run the Windows access-violation soak test at meaningfully higher
   repetition/concurrency/duration than this sandbox's bounded probes before
   any production dependency on Docling on Windows.
4. Expand the scanned corpus with real (non-synthetic, still non-case-data)
   scanned-document artifacts (paper texture, skew, genuine scanner noise) to
   validate whether this sandbox's synthetic corpus over- or under-states
   real-world OCR difficulty.
