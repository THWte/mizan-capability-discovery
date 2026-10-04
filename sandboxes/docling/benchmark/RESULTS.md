# Docling Sandbox — Benchmark Results

All results below are from actual runs against the synthetic fixtures in
`fixtures/` on this machine (Windows, Python 3.12.7, CPU-only, Docling 2.133.0).
Raw pytest output is saved in `pytest_raw_output.txt`. No real case data was used.

## 1. Format support — pass/fail

| Fixture | Format | Result | Notes |
|---|---|---|---|
| `sample_plain_text.pdf` | PDF (text) | ✅ Success | Full text and section order preserved |
| `sample_with_tables.pdf` | PDF (table) | ✅ Success | Table extracted, all 4 rows + header recovered correctly |
| `sample.docx` | DOCX | ✅ Success | Headings and table both recovered |
| `sample.xlsx` | XLSX | ✅ Success | Cell values recovered as markdown table |
| `sample.pptx` | PPTX | ✅ Success | Title, subtitle, and bullet text recovered |
| `sample_arabic.pdf` | PDF (Arabic) | ✅ Success, with caveat | See §2 — requires NFKC normalization |
| `sample_mixed_ar_en.pdf` | PDF (mixed) | ✅ Success, with caveat | Same NFKC caveat applies to the Arabic portion |
| `corrupted.pdf` | Malformed PDF | ✅ Fails cleanly | Adapter catches `ConversionError`; pipeline does not crash |
| `unsupported.xyz` | Unknown extension | ✅ Fails cleanly | Adapter catches `ConversionError` ("skipped") |
| missing file | N/A | ✅ Fails cleanly | Adapter returns a structured error, no exception escapes |

**18/18 automated tests passed** (`tests/test_docling_adapter.py`, full output in
`pytest_raw_output.txt`).

## 2. Arabic quality — the key finding

Raw Docling PDF text extraction for the Arabic fixture returns **Unicode
Presentation Forms**, not plain Arabic letters:

```
RAW   : ﻫﺬﺍ ﻣﺴﺘﻨﺪ ﺗﺠﺮﻳﺒﻲ ﺍﺻﻄﻨﺎﻋﻲ ...
NFKC  : هذا مستند تجريبي اصطناعي ...
ORIGIN: هذا مستند تجريبي اصطناعي ...  (exact match after NFKC)
```

- Word order and reading direction are **correct** once presentation forms are
  normalized.
- After applying `unicodedata.normalize("NFKC", text)`, the extracted text is an
  **exact match** to the original source text, including word order.
- This is almost certainly a property of how the PDF's content stream stores
  glyphs (presentation-form codepoints, common from non-Unicode-aware PDF
  generators — including our own `reportlab`-based fixture, which required
  `arabic-reshaper` + `python-bidi` to render correctly at all), not a bug unique
  to Docling. But **Docling does not normalize this automatically**, so any
  consumer must add an NFKC normalization step before treating the text as
  reliable Arabic input for NLP, search indexing, or display.
- **Actionable conclusion**: MIZAN's Docling adapter (or the layer above it) MUST
  apply Unicode NFKC normalization to all extracted text before further
  processing. This is implemented as a documented, testable requirement in
  `tests/test_docling_adapter.py::test_arabic_text_matches_source_after_nfkc_normalization`.
- **Not yet tested**: OCR-based Arabic extraction (i.e., Arabic text in a
  *scanned/rasterized* document, as opposed to a text-layer PDF). This fixture
  only validates text-layer extraction. Real court/case scans would exercise
  Docling's RapidOCR Arabic recognition path, which has materially different
  (and unverified) accuracy characteristics — this is an open gap, not a
  validated capability. See `COMPARISON_AND_DECISION.md` §"Open questions".

## 3. Table extraction accuracy

- PDF table (4 data rows + header, 4 columns): **all cell values recovered
  correctly** (`EX-001`..`EX-004`, descriptions, dates, statuses all present and
  matched by automated assertions).
- DOCX table (2 data rows + header, 3 columns): **all cell values recovered
  correctly**.
- No tables were present in the PPTX/XLSX fixtures as "Table" objects (XLSX
  sheets are exported as a markdown table representation of the whole sheet,
  which worked correctly for our fixture).

## 4. Content ordering

- Section order in the plain-text PDF (`Section 1` → `Section 2` → `Section 3`)
  was preserved exactly in the extracted output.

## 5. Error handling

- A deliberately corrupted PDF (invalid binary body) and a file with an
  unsupported extension both failed **without raising an unhandled exception**
  out of the adapter. Docling raises a `ConversionError` internally; the adapter
  catches it and returns a structured failure result (`success=False`,
  populated `errors`).
- A missing file path is detected before calling Docling and fails cleanly.

## 6. Stability across repeated runs

- Re-running the same PDF twice in the same process produced **byte-identical**
  `full_text` output and the same table count. No evidence of run-to-run
  non-determinism was observed in this limited test.

## 7. Performance (CPU-only, this machine, single process)

| Fixture | Elapsed (default pipeline, OCR enabled) | Elapsed (`do_ocr=False`) |
|---|---|---|
| `sample_plain_text.pdf` (1 page, text-only) | ~36.4s | ~12.3s |
| `sample_with_tables.pdf` (1 page, table) | ~48.2s | not tested |
| `sample_arabic.pdf` (1 page, text-only) | ~12.0s | not tested |
| `sample_mixed_ar_en.pdf` (1 page, text-only) | ~2.3s | not tested |
| `sample.docx` | ~0.2s | n/a (DOCX path doesn't invoke the PDF/OCR pipeline) |
| `sample.pptx` | ~0.03s | n/a |
| `sample.xlsx` | ~0.0s | n/a |

**Key finding**: Docling's `DocumentConverter()` default configuration runs full
OCR on every PDF page regardless of whether the page already has a text layer.
For a trivial 1-page, text-only PDF this cost **~36 seconds** on CPU; disabling
OCR explicitly (`PdfPipelineOptions(do_ocr=False)`) cut this to **~12 seconds**.
At MIZAN's expected case-file volumes, this is operationally significant:
production use would need either (a) explicit OCR-mode selection based on
whether a PDF is born-digital vs. scanned, (b) GPU acceleration, or (c) both.
The ~12s residual cost even without OCR (layout + table-structure model
inference) is itself non-trivial for a single page on CPU.

## 8. First-run network dependency (privacy/local-first impact)

On first use, Docling's default pipeline **downloads ML models from the
internet** on demand:
- RapidOCR detection/classification/recognition weights from `modelscope.cn`
  (~30MB total)
- A layout model from the Hugging Face Hub (unauthenticated, with a rate-limit
  warning logged)

After this first download, models are cached locally
(`.venv/Lib/site-packages/rapidocr/models/` and the HF cache) and subsequent
runs do not re-download. **This means Docling is not local-first out of the
box**: a genuinely air-gapped or offline-first MIZAN deployment would need to
pre-provision/vendor these model weights as part of its build or deployment
process, not assume first-run internet access.

## 9. Stability warning observed

During the pytest run, the console intermittently printed:

```
Windows fatal exception: access violation
```

from a background thread inside `pydantic`/the OCR inference stack, without
failing any test or crashing the process. This did not reproduce consistently
and did not cause a test failure in this run, but it is a signal worth
monitoring — repeated or escalating access violations under production load
(concurrent documents, larger PDFs) should be treated as a real stability risk
until investigated further, not dismissed because tests currently pass.
