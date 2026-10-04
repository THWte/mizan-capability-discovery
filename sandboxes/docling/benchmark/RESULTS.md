# Docling Sandbox — Benchmark Results (Revision 2)

All results below are from actual runs against the synthetic fixtures in
`fixtures/` on this machine (Windows, Python 3.12.7, CPU-only, Docling 2.133.0,
RapidOCR via `rapidocr` package, onnxruntime + torch backends both present).
No real case data was used anywhere in this sandbox.

This revision supersedes Revision 1 wherever findings changed after
implementing real OCR routing, NFKC-in-adapter, the scanned Arabic corpus, and
CER/WER measurement. Nothing from Revision 1 was deleted silently — corrected
or superseded claims are marked explicitly below.

## 1. Format support — pass/fail (born-digital / text-layer documents)

| Fixture | Format | Result | Notes |
|---|---|---|---|
| `sample_plain_text.pdf` | PDF (text) | ✅ Success | Full text and section order preserved; routed `ocr_mode=born_digital`, OCR OFF |
| `sample_with_tables.pdf` | PDF (table) | ✅ Success | Table extracted, all 4 rows + header recovered correctly |
| `sample.docx` | DOCX | ✅ Success | Headings and table both recovered |
| `sample.xlsx` | XLSX | ✅ Success | Cell values recovered as markdown table |
| `sample.pptx` | PPTX | ✅ Success | Title, subtitle, and bullet text recovered |
| `sample_arabic.pdf` | PDF (Arabic, text layer) | ✅ Success, with caveat | See §2 — requires adapter-side NFKC normalization |
| `sample_mixed_ar_en.pdf` | PDF (mixed, text layer) | ✅ Success, with caveat | Same NFKC caveat applies to the Arabic portion |
| `corrupted.pdf` | Malformed PDF | ✅ Fails cleanly | Adapter catches the conversion error; pipeline does not crash |
| `unsupported.xyz` | Unknown extension | ✅ Fails cleanly | Adapter catches the conversion error ("skipped") |
| missing file | N/A | ✅ Fails cleanly | Adapter returns a structured error, no exception escapes |

## 2. Arabic quality on text-layer PDFs — NFKC now applied INSIDE the adapter

Raw Docling PDF text extraction for the text-layer Arabic fixture returns
**Unicode Presentation Forms**, not plain Arabic letters. This is now handled
as a first-class adapter contract, not a test-only workaround:

- `NormalizedDocumentResult.raw_text` = exactly what Docling returned
  (presentation forms), preserved for provenance/audit.
- `NormalizedDocumentResult.normalized_text` = `unicodedata.normalize("NFKC",
  raw_text)`, computed **inside `DoclingAdapter.convert()`** (see
  `adapter.py::normalize_text` and `DoclingAdapter.convert`), not by a test
  helper. `tests/test_docling_adapter.py::
  test_adapter_performs_nfkc_normalization_itself_not_the_test` asserts
  `result.normalized_text == NFKC(result.raw_text)` directly off the adapter's
  own output, and performs no normalization of its own.
- After normalization, extracted text is an **exact match** to the original
  source text, including word order, for both the pure-Arabic and
  mixed-Arabic/English text-layer fixtures.

## 3. OCR routing — now implemented in code, not just described

`adapter.py::_classify_pdf_for_ocr` inspects every PDF with `pypdf` BEFORE
calling Docling, independent of Docling's own behavior:

| ocr_mode | Trigger | OCR | Verified by |
|---|---|---|---|
| `born_digital` | ≥40 non-whitespace chars/page extractable via `pypdf` | OFF | `test_ocr_routing.py::test_born_digital_pdf_routes_ocr_off`, `test_born_digital_pdf_is_fast_without_ocr` |
| `scanned` | 0 extractable chars across all pages | ON | `test_ocr_routing.py::test_scanned_pdf_routes_ocr_on`, `test_scanned_pdf_actually_extracts_text_via_ocr` |
| `ambiguous` | >0 but <40 chars/page (sparse/unreliable text layer) | ON (safe fallback) + explicit warning | `test_ocr_routing.py::test_ambiguous_pdf_routes_ocr_on_with_warning` |
| `unknown` | pre-check itself raised | ON (safe default) + warning | covered by the "unknown" branch in `_classify_pdf_for_ocr`; not hit in this fixture set |
| `not_applicable` | non-PDF format | n/a | `test_ocr_routing.py::test_non_pdf_formats_mark_ocr_routing_not_applicable` |

The decision is recorded on every result as `ocr_mode`, `ocr_reason`, and
`ocr_engine` — these are real dataclass fields on `NormalizedDocumentResult`,
populated by `DoclingAdapter.convert()`, not documentation-only claims.

**Routing performance confirmation**: `sample_plain_text.pdf` (born-digital,
OCR OFF) completed in well under the ~36s forced-OCR baseline from Revision 1
(see §7 for the full cold/warm breakdown).

## 4. CRITICAL FINDING — Docling's default OCR language is Chinese, not Arabic

This was **not caught in Revision 1** because only text-layer Arabic PDFs were
tested (no OCR was ever exercised on Arabic script). Testing the new
**scanned** Arabic corpus (true raster PDFs, zero text layer) exposed it
immediately:

- Docling's default `RapidOcrOptions()` sets `lang=['ch']` (Chinese).
  Run against a clean scanned Arabic PDF with the DEFAULT config, RapidOCR
  returned pure garbage with embedded CJK characters, e.g.:
  `'9-A94?门-91q-7?]'` for a page whose actual content was
  `'هذا مستند ممسوح ضوئيًا اصطناعي وليس ملف قضية حقيقي...'` — i.e. **Arabic
  script is misrecognized as other scripts, not flagged as unsupported.**
- On the mixed Arabic/English fixture under the default config, the **English
  portions were recovered correctly** and the **Arabic portions were silently
  dropped entirely** (not garbled — just absent from the output), which is an
  especially dangerous failure mode for a legal-document pipeline: a
  downstream reader would see a coherent-looking English fragment and have no
  signal that Arabic content existed on the page at all.
- **Fix applied in this sandbox**: `adapter.py` now explicitly configures
  `RapidOcrOptions(lang=["arabic", "en"])` for the OCR-on converter. This
  triggers a one-time additional download (`arabic_PP-OCRv5_rec_mobile.onnx`,
  ~7.65MB from `modelscope.cn`) and an `onnxruntime` backend dependency not
  previously installed in this sandbox (`pip install onnxruntime` was
  required — torch-only RapidOCR raised `ImportError: onnxruntime is not
  installed` for the Arabic-language recognition model specifically).
- **This is not documented prominently in Docling's own README/quickstart.**
  A team integrating Docling for Arabic documents without this sandbox's
  investigation would very likely ship **silent Arabic OCR failure** believing
  OCR "worked" because `success=True` and English/numeric content looked fine.

## 5. Scanned Arabic OCR quality — CER/WER (measured, not assumed)

Corpus: `fixtures/generate_scanned_corpus.py` — 5 synthetic, fully raster
(zero text layer, confirmed via `pypdf.extract_text()` returning empty string
for all 5 files) Arabic PDFs rendered via PIL + TrueType font, embedded as
images only (no PDF text operators). Ground truth stored as sidecar
`.expected.txt` files. OCR run through the real adapter path (`ocr_mode=
scanned`, `ocr_engine=rapidocr(lang=arabic,en)`). CER/WER computed with a
dependency-free Levenshtein implementation in `benchmark/ocr_metrics.py`
(whitespace-normalized before scoring). Full reproducible data in
`benchmark/ocr_quality_results.json` (expected text, extracted text, and
scores for every case).

| Case | CER | WER | Time (s) | Notes |
|---|---|---|---|---|
| `scanned_arabic_clear` | 0.686 | 0.895 | 7.8 | Clear, high-quality synthetic scan. Still a majority of characters wrong. |
| `scanned_arabic_numeric` | 0.675 | 0.889 | 3.8 | Arabic + numbers/date/amount. |
| `scanned_mixed_ar_en` | 0.361 | 0.433 | 5.3 | Best result — English portions recovered correctly, pulling the aggregate score down; Arabic portion still weak. |
| `scanned_arabic_table` | 0.818 | **1.524** | 10.2 | **Fails the sanity ceiling (WER>1.5, i.e. more word-level edits than words in the reference) — recorded as a genuine test FAILURE, not hidden.** Numeric/date/ID cells are read correctly; Arabic header/status words are lost or badly mangled, and table structure is not reconstructed as a table at all in the OCR-only path. |
| `scanned_arabic_low_quality` | 1.0 | 1.0 | 5.6 | **Total OCR failure after Gaussian-blur degradation.** Documented honestly in `test_low_quality_scan_ocr_outcome_is_recorded_honestly`, not forced to pass. |

**Honest conclusion: even with the correct language model explicitly
configured, Arabic OCR quality on this engine/configuration is POOR — CER in
the 36%–100% range, WER in the 43%–152% range — on clean, synthetic, high-
contrast scans. This is nowhere near production-usable for legal documents
without a materially different OCR engine/model, additional tuning (e.g.
`model_size="medium"`, a different backend, or a specialized Arabic OCR
engine entirely), and a much larger, more representative evaluation corpus.**
`success=True` at the adapter level was never treated as evidence of quality
— every number above came from scoring actual extracted text against actual
ground truth.

**Important corpus caveat**: all 5 scanned fixtures are system-font synthetic
renders of RTL-shaped text, not real scanned-paper artifacts (no paper
texture, ink bleed, skew, or genuine scanner noise beyond the deliberate blur
variant). This is a reasonable first OCR smoke test but likely UNDERSTATES
real-world scanned-document difficulty, not overstates it.

## 6. Table extraction accuracy (born-digital path only; OCR-path tables are
covered by §5's `scanned_arabic_table` result)

- PDF table (4 data rows + header, 4 columns), born-digital: **all cell
  values recovered correctly**.
- DOCX table (2 data rows + header, 3 columns): **all cell values recovered
  correctly**.

## 7. Cold start vs. warm processing (separated per this revision's
requirement — Revision 1 conflated these)

Measured via `benchmark/benchmark_cold_warm.py`, full JSON in
`benchmark/cold_warm_results.json`. Models were already cached locally from
earlier sandbox runs in this environment (this measures load time, not
network download time — see §9 for the offline/local-first test, which is
separate from this timing).

| Phase | What it measures | Elapsed | RSS delta |
|---|---|---|---|
| **Cold start** | `DoclingAdapter()` construction (pipeline init, loading cached layout + OCR model weights into memory) | **22.9s** | +319 MB |
| **Warm, born-digital/OCR-off**, run 1 (first conversion after cold start) | includes additional lazy-loaded layout-model weights not loaded at construction time | 20.4s | — |
| **Warm, born-digital/OCR-off**, run 2 | steady-state | 7.0s | — |
| **Warm, born-digital/OCR-off**, run 3 | steady-state | 2.6s | — |
| **Warm, scanned/OCR-on**, run 1 (first OCR call) | includes additional lazy-loaded RapidOCR weights not loaded at construction time | 18.2s | — |
| **Warm, scanned/OCR-on**, run 2 | steady-state | 9.9s | — |
| **Warm, scanned/OCR-on**, run 3 | steady-state | 10.0s | — |
| RSS after all runs | cumulative process memory | — | 628 MB total |

**Key finding not visible in Revision 1**: even after `DoclingAdapter()`
construction completes, the FIRST conversion of each pipeline family
(born-digital path, scanned/OCR path) pays an additional one-time lazy-load
cost (~13–18s) beyond steady-state (~2.6–10s). A long-running MIZAN service
process amortizes this; a short-lived/serverless/one-shot invocation pattern
would pay close to the cold-start-plus-first-conversion cost
(**~43s for born-digital, ~41s for scanned**) on every invocation.

## 8. Windows Access Violation Investigation

A `Windows fatal exception: access violation` message (printed via Python's
`faulthandler`, from background thread(s), not a catchable Python exception)
has been observed during pytest runs in this sandbox. This section documents
a dedicated investigation, not a one-line dismissal.

**Evidence actually captured** (one full run, this sandbox, this machine):

```
Windows fatal exception: access violation
Thread 0x000045d8 (most recent call first):
  File ".../docling_parse/pdf_parser.py", line ??? in get_connected_shape_bounding_boxes
```

(Several other threads in the same dump were idle, blocked in
`threading.py` `wait()` inside Docling's own batch-processing threads —
not implicated as the fault site themselves.)

**Investigation performed** (`tests/test_windows_stability.py`):

| Probe | Method | Result |
|---|---|---|
| Repeated sequential runs, same document | 5x in-process repetition | All 5 succeeded; output byte-identical across runs; no test failure |
| Sequential runs, multiple different documents | 4 different fixtures (born-digital, table, Arabic, scanned/OCR) back-to-back | All succeeded; no test failure |
| Bounded concurrent runs | `ThreadPoolExecutor(max_workers=2)`, 2 documents | Both succeeded; no test failure; no additional crash signal observed in this specific run |

**Effect on process/results**: In the one full-suite run where the message was
captured, it printed to stderr **after** pytest had already reported
`PASSED` for the last collected test, and it changed the host shell's visible
exit code to non-zero in a wrapping process despite pytest's own summary
reporting all tests passed at that point — i.e. it is consistent with a fault
during interpreter/thread teardown after the test session's own work was
already complete, not a fault that corrupted any individual test's result.
This sandbox could NOT reproduce it on-demand inside the dedicated
repeated/sequential/concurrent probes above, only observed it opportunistically
during full-suite runs.

**Second occurrence (Revision 2 re-run, after the NFKC/OCR-routing/CER-WER
changes in this revision)**: the fault was observed again in the full
49-test re-run performed for this revision, appearing in the stderr stream
between `test_sequential_runs_across_multiple_different_documents` and
`test_bounded_concurrent_runs_do_not_crash_the_process` (both of which still
reported `PASSED`). This is now **2 observed occurrences across 2 full-suite
runs on this machine** (occurrence count tracked honestly, not rounded down
to "rare" or up to "frequent" without more data) — consistent with the fault
being tied to the overall PDF-parsing workload rather than to any one
specific test, and reinforcing that it should not be dismissed as a fluke.

**Classification: `UNRESOLVED` — not "Low".**

Reasoning for not classifying this as Low severity merely because pytest
assertions did not fail:
- It is a native-code (non-Python) access violation, which is categorically
  a different class of risk than a Python-level test assertion failing.
- The one captured stack trace implicates `docling_parse` (Docling's own C++
  PDF-parsing backend), not RapidOCR/PyTorch as might be assumed — this
  sandbox cannot rule out other paths in other runs, but has concrete
  evidence against defaulting to "it's probably a PyTorch/OCR threading
  issue."
- It was not reliably reproducible inside this sandbox's bounded probes,
  which means absence of evidence here is not evidence of absence under
  different load, document shapes, or longer-running processes.
- Under sustained production load (many more documents, higher concurrency,
  longer process lifetimes than tested here), the same underlying condition
  could plausibly manifest more frequently or with worse effect; this
  sandbox's bounded, short-duration probes are not a substitute for that kind
  of soak testing.

**Risk attribution: Docling's `docling_parse` native backend (best available
evidence) — NOT confirmed to be RapidOCR or PyTorch.** This is the single
largest unresolved operational risk identified in this entire sandbox and
should be escalated to dedicated soak/stress testing (much higher repetition
counts, longer-running processes, varied document sizes, real concurrency
levels) before any production reliance on Docling on Windows.

## 9. Offline / Local-first behavior

Tested via `tests/test_offline_local_first.py`, which launches a **separate
subprocess** with `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, and
`HF_ENDPOINT` pointed at an unreachable address, after models were already
cached from earlier runs in this sandbox.

- **Born-digital conversion**: succeeds fully offline. ✅
- **Scanned/OCR conversion (including the Arabic-language model)**: succeeds
  fully offline once the Arabic RapidOCR weights are cached. ✅

**Models required and where they are cached** (this environment):

| Model | Purpose | Source | Cache location |
|---|---|---|---|
| Docling layout model (`docling-project/docling-layout-heron`) | Page layout analysis | Hugging Face Hub | `%USERPROFILE%\.cache\huggingface\hub\models--docling-project--docling-layout-heron` |
| Docling table/structure models (`docling-project/docling-models`) | Table structure recognition | Hugging Face Hub | `%USERPROFILE%\.cache\huggingface\hub\models--docling-project--docling-models` |
| `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | Used internally by Docling's pipeline | Hugging Face Hub | `%USERPROFILE%\.cache\huggingface\hub\...` |
| RapidOCR detection/classification/default-recognition weights (`PP-OCRv6_det_small`, `ch_ptocr_mobile_v2.0_cls_mobile`, `PP-OCRv6_rec_small`, both `.pth` and `.onnx`) | OCR (default Chinese-language config) | `modelscope.cn` | `<venv>\Lib\site-packages\rapidocr\models\` |
| `arabic_PP-OCRv5_rec_mobile.onnx` (~7.65MB) | OCR recognition, Arabic script (see §4) | `modelscope.cn` | `<venv>\Lib\site-packages\rapidocr\models\` |

**Pre-provisioning for a genuinely air-gapped deployment**: vendor/bundle the
contents of both cache locations above as part of the MIZAN build/deployment
artifact (not left to first-run download), and set `HF_HUB_OFFLINE=1` /
`TRANSFORMERS_OFFLINE=1` in the runtime environment to make the "no network"
assumption explicit and fail loudly rather than silently retry.

**If models are NOT present and there is no internet access**: Docling/
RapidOCR will raise a download/connection error at the point the missing
model is first needed (not at adapter construction time for every model —
some are lazy-loaded on first use per §7). This was not independently
re-verified by deleting the cache in this sandbox (doing so would have
required re-downloading ~40MB+ of models to restore the environment for
further testing), but is consistent with standard Hugging Face Hub /
`modelscope.cn` client behavior. **This is a documented inference, not a
directly observed test in this sandbox — flagged as such rather than
asserted as a verified fact.**

**No document content was sent to any external service** in any test in this
sandbox — only model weight downloads touch the network, and those carry no
document content.

## 10. Stability / determinism across repeated runs (adapter-contract level,
distinct from §8's native-level investigation)

- Re-running the same PDF repeatedly in the same process produces
  **byte-identical** `raw_text` and `normalized_text` output and the same
  table count, for both born-digital and OCR paths tested.
