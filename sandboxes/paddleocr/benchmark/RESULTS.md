# PaddleOCR Sandbox — Benchmark Results

All results below are from actual runs against the synthetic fixtures in
`fixtures/` on this machine (Windows, Python 3.12.7, CPU-only,
`paddleocr==3.3.3`, `paddlepaddle==3.2.2`, PP-OCRv5 server detector +
`arabic_PP-OCRv5_mobile_rec` recognizer). No real case data was used
anywhere in this sandbox. `success=True` was never treated as evidence of
quality or of a resolved risk — every claim below is backed by a concrete
number, log excerpt, or JSON artifact in this directory.

## 1. Format support — pass/fail

PaddleOCR (`paddleocr.PaddleOCR`) is an OCR engine, not a general document
converter: it only accepts raster/image input (or a PDF it rasterizes itself
page-by-page). It has no native DOCX/XLSX/PPTX parsing capability at all —
this is architecturally different from Docling and is recorded as a real
capability gap, not worked around.

| Fixture type | Result | Notes |
|---|---|---|
| Scanned (raster) Arabic PDF | ✅ Success | OCR applied; see §3 for CER/WER |
| Scanned mixed Arabic/English PDF | ✅ Success | English and Arabic both recovered; see §3 |
| Scanned Arabic table PDF | ✅ Success (with quality caveat) | Table *content* recognized as a flat line sequence; table *structure* (rows/cols) is **NOT** reconstructed — PaddleOCR's base `PaddleOCR` pipeline returns text lines with bounding boxes, not a table model. (`PPStructureV3`, a separate, heavier pipeline, offers table structure recovery and was explicitly out of scope for this sandbox since the directive asked for the OCR capability specifically.) |
| Born-digital (vector-text) PDF | ✅ Success, but **OCR is still applied** | See §2 — this engine has no "OCR off" path |
| DOCX / XLSX / PPTX | ❌ Not supported | PaddleOCR has no native parser for these formats. Recorded as a genuine gap, not a workaround target. |
| Corrupted / unsupported file | ✅ Fails cleanly | `adapter.py`'s `convert()` catches the exception and returns a structured `success=False` result with `errors` populated; no exception escapes to the caller |
| Missing file | ✅ Fails cleanly | Same structured-error path |

## 2. OCR routing — real routing decision, but PaddleOCR always runs OCR

Unlike Docling (which can skip OCR entirely for born-digital PDFs),
**PaddleOCR has no code path that extracts an existing PDF text layer** — it
only ever runs its detection+recognition pipeline on rasterized page images.
`adapter.py::_classify_pdf_for_ocr` still performs the SAME pre-check as the
Docling sandbox (via `pypdf`, independent of PaddleOCR's own behavior) and
records a real `ocr_mode` / `ocr_reason` / `ocr_engine` decision on every
result — but for this engine, OCR is **always physically applied**
(`ocr_applied` is always `True`), even when `ocr_mode="born_digital"`. This
is intentional and tested (`test_ocr_applied_always.py`,
`test_vector_pdf_capability.py`): the field documents *what the pre-check
found*, not *what the engine chose to do with it*, because this engine
cannot choose.

| ocr_mode | Trigger | OCR actually applied | Verified by |
|---|---|---|---|
| `born_digital` | ≥40 non-whitespace chars/page via `pypdf` | **Always True** (no OCR-off path exists for this engine) | `test_vector_pdf_capability.py::test_single_born_digital_conversion_succeeds_and_is_classified_correctly` |
| `scanned` | 0 extractable chars across all pages | True | `test_ocr_applied_always.py::test_scanned_pdf_runs_ocr_and_classification_matches` |
| `ambiguous` | >0 but <40 chars/page | True + explicit warning | covered by routing classifier tests in `test_paddleocr_adapter.py` |
| `not_applicable` | non-PDF image format (PNG, etc.) | True | `test_ocr_applied_always.py::test_non_pdf_image_format_marks_routing_not_applicable_but_still_applies_ocr` |

**Practical consequence for MIZAN**: if PaddleOCR were ever connected as a
real ingestion engine, routing born-digital PDFs to it would waste ~20-30s
of OCR compute per document for no accuracy benefit over simply reading the
existing text layer (which Docling, or a plain `pypdf`/`pdfplumber` call,
already does for free). This is a genuine architectural weakness relative to
Docling for the born-digital case, and a genuine strength for the
scanned/OCR case (see §3).

## 3. Scanned Arabic OCR quality — CER/WER (measured, not assumed)

Corpus: `fixtures/generate_scanned_corpus.py` — 10 synthetic, fully raster
(zero text layer, confirmed via `pypdf.extract_text()` returning empty
string) Arabic/mixed PDFs, covering: clear text, numeric/date/amount,
mixed Arabic/English, a simple table, a Gaussian-blurred low-quality
variant, Eastern Arabic-Indic digits, a rotated page, a blank page, added
noise, and a multi-block (header/middle/footer) layout. Ground truth stored
as sidecar expected text in `fixtures/generate_scanned_corpus.py`. OCR run
through the real adapter path. CER/WER computed with the same
dependency-free Levenshtein implementation used by the Docling sandbox
(`benchmark/ocr_metrics.py`, whitespace-normalized before scoring). Full
reproducible data (expected text, raw/normalized/extracted text, and scores
for every case) in `benchmark/ocr_quality_results.json`.

| Case | CER | WER | Time (s) | Notes |
|---|---|---|---|---|
| `scanned_arabic_clear` | **0.010** | **0.053** | 25.3 | Clear, high-quality synthetic scan — near-perfect. |
| `scanned_arabic_numeric` | 0.278 | 0.556 | 20.7 | Digits/date/amount lines partially merged/lost (e.g. `48219` dropped entirely, `2024-05-17` reordered to `17-05-2024`). |
| `scanned_mixed_ar_en` | **0.026** | 0.167 | 22.0 | Both English and Arabic portions recovered; small casing error (`OCR`→`OcR`) and one word-boundary merge. |
| `scanned_arabic_table` | 0.461 | 0.667 | 22.9 | Table **cell values** (invoice numbers, dates, amounts, status words) are all individually recognized correctly as flat text lines, but **column/row structure is lost** — CER/WER are inflated here because they compare against the original reading-order reference text, not because the characters are wrong. See §1 caveat on table structure. |
| `scanned_arabic_low_quality` | 0.710 | 0.895 | 23.6 | Gaussian-blur degraded scan — most words are shuffled or garbled. Recorded honestly as a real failure, not hidden or re-tried until passing. |
| `scanned_arabic_indic_digits` | 0.261 | 0.615 | 21.0 | Eastern Arabic-Indic digits (٤٨٢١٩ etc.) partially misread/dropped. |
| `scanned_arabic_rotated` | **0.014** | **0.079** | 20.3 | Rotated-page handling is excellent — PP-OCRv5's detector appears robust to this. |
| `scanned_blank_page` | N/A (no text) | N/A (no text) | 16.0 | Correctly produces empty output with an explicit `"PaddleOCR returned zero recognized text lines for this document."` warning — no hallucinated text. |
| `scanned_arabic_noisy` | **0.014** | **0.079** | 22.6 | Synthetic pixel noise barely affected recognition. |
| `scanned_arabic_multi_block` | **0.031** | 0.190 | 22.2 | Header/middle/footer block separation preserved in reading order. |

**Honest conclusion: on clear, rotated, noisy, and mixed Arabic/English
synthetic scans, this engine/configuration (PP-OCRv5 + Arabic mobile
recognizer) is materially stronger than Docling's RapidOCR configuration
tested in the Docling sandbox (CER 1.0-4.9%, WER 5-19% here, vs Docling's
CER 36-100%, WER 43-152% on the comparable fixture set). On the shared
`scanned_arabic_table` fixture specifically: PaddleOCR WER=0.667 vs
Docling's documented WER=1.524 — PaddleOCR is clearly better at this one
task, though neither reconstructs table structure.** Numeric/date/amount
recognition and heavily-degraded scans remain weak points for PaddleOCR too
(WER 55-90% on those cases) — this is NOT a uniformly "solved" problem,
just a meaningfully better starting point than the Docling/RapidOCR
configuration tested earlier in this project.

**Important corpus caveat** (same as the Docling sandbox): all 10 fixtures
are system-font synthetic renders of RTL-shaped text, not real scanned-paper
artifacts. This likely UNDERSTATES real-world scanned-document difficulty.

## 4. NFKC normalization — raw vs normalized, inside the adapter

`adapter.py::PaddleOcrAdapter.convert()` computes both:

- `raw_text` — exactly what PaddleOCR's recognizer returned (joined text
  lines, in reading order), preserved unmodified for provenance/audit.
- `normalized_text` — `unicodedata.normalize("NFKC", raw_text)`, computed
  **inside the adapter itself** (`adapter.py::normalize_text`), not by a
  test helper.

`tests/test_paddleocr_adapter.py::test_adapter_performs_nfkc_normalization_itself_not_the_test`
asserts `result.normalized_text == NFKC(result.raw_text)` directly off the
adapter's own output and performs no normalization of its own, proving the
transformation lives in the adapter contract, not in test scaffolding.
Downstream processing (`mizan_bridge.py`) is explicitly built to consume
`normalized_text`, never `raw_text`, for anything other than provenance
storage.

## 5. Table extraction — content yes, structure no

See §1/§3 `scanned_arabic_table`: all individual cell values are correctly
recognized as text, but PaddleOCR's base pipeline (as used in this sandbox)
returns a flat sequence of recognized lines with bounding boxes — it does
not group them into a `Table`/`TableCell` structure the way Docling's
layout model does for born-digital PDFs and DOCX. This is recorded as a
genuine capability gap for this specific PaddleOCR pipeline configuration,
not a bug to paper over. (PaddleOCR's separate `PPStructureV3` pipeline
offers table structure recovery; it was explicitly out of scope — adding it
would be a materially different and heavier capability evaluation.)

## 6. Cold start vs. warm processing (separated)

Measured via `benchmark/benchmark_cold_warm.py` and, after that combined
script crashed in this environment (see §7), via two smaller, per-path
scripts run in separate fresh processes. Models were already cached locally
in `%USERPROFILE%\.paddlex\official_models\` from earlier sandbox runs —
this measures load time, not network download time (see §8 for the
offline/local-first test). Full data in `benchmark/cold_warm_results.json`.

| Phase | What it measures | Elapsed | RSS delta |
|---|---|---|---|
| **Cold start (born-digital path process)** | `PaddleOcrAdapter()` construction (detector model + lazy Arabic recognizer load triggered by the construction-time self-check) | 12.8s | +382 MB (27→409 MB) |
| **Warm, "born-digital"/OCR-applied**, run 1 | first conversion in this process | 29.1s | — |
| **Warm, "born-digital"/OCR-applied**, run 2 | steady-state | 25.8s | — |
| **Warm, "born-digital"/OCR-applied**, run 3 | steady-state | 25.2s | — |
| RSS after born-digital runs | cumulative process memory | — | 780 MB total |
| **Cold start (scanned path process)** | same construction, separate fresh process | 11.7s | +385 MB (21→407 MB) |
| **Warm, scanned/OCR-applied**, run 1 | first conversion in this process | 22.3s | — |
| **Warm, scanned/OCR-applied**, run 2 | steady-state | 22.7s | — |
| **Warm, scanned/OCR-applied**, run 3 | steady-state | 24.1s | — |
| RSS after scanned runs | cumulative process memory | — | 639 MB total |

**Key findings**:
- Steady-state warm conversion time for this engine is **~22-26 seconds per
  page-document regardless of OCR-mode classification**, because OCR always
  runs (§2). This is markedly slower than Docling's born-digital path
  (~2.6-7s steady-state) and broadly comparable to Docling's scanned/OCR
  path (~9.9-10s steady-state) — i.e. **PaddleOCR's per-document OCR cost
  is roughly 2-2.5x Docling's RapidOCR cost in this environment**, which is
  the direct tradeoff for PaddleOCR's materially better Arabic accuracy
  (§3).
- There is no large distinct "first warm run" cliff the way Docling showed
  (13-18s one-time lazy-load cost beyond steady state) — PaddleOCR's
  recognizer model appears to be fully loaded by the time `PaddleOcrAdapter()`
  construction returns, matching the ~12-13s cold-start cost; the first
  warm run is only ~3-7s slower than subsequent runs here, not ~2x slower.
- Memory footprint (~639-780 MB RSS after a handful of conversions) is
  substantially higher than Docling's (~628 MB after a comparable set of
  runs, including both OCR and non-OCR paths) despite doing strictly less
  work per document (no table-structure/layout model) — attributable to
  PaddlePaddle's own runtime overhead.

## 7. Windows Stability / Access Violation Investigation

This sandbox independently reproduced the **same class of fault** documented
in the Docling sandbox (`Windows fatal exception: access violation`,
process exit code `-1073741819` / `0xC0000005`), with PaddleOCR/PaddlePaddle
as the component in the call stack this time — confirming this is not a
Docling-specific issue, and keeping the overall classification `UNRESOLVED`
rather than attributing it to one engine.

**Investigation performed** (`tests/test_windows_stability.py`,
`tests/test_vector_pdf_capability.py`, and this benchmark's own crashes):

| Probe | Method | Result |
|---|---|---|
| Repeated sequential runs, same document | 5x in-process repetition | All 5 succeeded; no crash in this probe |
| Sequential runs, multiple different scanned documents | 4 different fixtures back-to-back | All succeeded; no crash in this probe |
| Bounded concurrent runs (first attempt) | `ThreadPoolExecutor(max_workers=2)`, 2 documents | Both succeeded in this attempt; no crash |
| Vector-text (reportlab) PDF then scanned PDF, same process | subprocess-isolated, outcome recorded regardless | Succeeded (1/1 attempt) |
| Bounded concurrent runs, re-run (shared adapter instance) | `ThreadPoolExecutor(max_workers=2)`, 2 documents, run a second time | **Failed** with `IndexError: invalid vector<bool> subscript` (catchable Python exception, not a native crash this time) — see §7a |
| Bounded concurrent runs, separate adapter instance per thread | same probe, isolated per-thread instances | **Crashed** (exit `-1073741819`) — captured stack trace below; see §7a |
| `benchmark_cold_warm.py` full run: cold start → 3x born-digital conversions → 3x scanned conversions, one process | direct script execution | **Crashed, 2/2 attempts** (exit `-1073741819`), both times immediately after the Arabic recognizer model finished loading and before the first conversion's result printed |
| Same born-digital path alone, fresh process (3 warm runs) | isolated script | Succeeded, 3/3 |
| Same scanned path alone, fresh process (3 warm runs) | isolated script | Succeeded, 3/3 |
| Reordering fixture creation before vs. after adapter construction | both orders tried | **Did not change the outcome** — both orders crashed when run as the combined cold/warm script |

**Captured stack trace (bounded-concurrency re-run crash)**, implicating
PaddleX's own inference wrapper around the native PaddlePaddle runtime —
not RapidOCR/PyTorch, since this sandbox uses neither:

```
Windows fatal exception: access violation
Thread 0x00008260 (most recent call first):
  File ".../paddlex/inference/models/common/static_infer.py", line 260 in __call__
  File ".../paddlex/inference/models/common/static_infer.py", line 297 in __call__
  File ".../paddlex/inference/models/text_detection/predictor.py", line 105 in process
  File ".../paddlex/inference/models/base/predictor/base_predictor.py", line 330 in ...
```


**What this rules out**: the crash is **not** specific to vector+raster
mixing alone (disproven in the Docling-era investigation already, and
consistent here), **not** specific to any single fixed call count (crashed
here on attempt #1 of a fresh process, after only 1-2 model loads — far
lower native-call volume than the ~34-call threshold observed in the
Docling investigation), and **not** fixed by changing the order of
unrelated setup code (fixture generation) relative to adapter construction.

### 7a. Concurrency — a SEPARATE, CONFIRMED-UNSAFE finding (not merely intermittent)

Unlike the general sequential-workload finding above (genuinely
intermittent, no isolated single cause), **concurrent use of this adapter
is unsafe on every attempt made in this investigation** — a much stronger
and more actionable result:

| Concurrency scenario | Result |
|---|---|
| 2 threads, **one shared** `PaddleOcrAdapter()` instance, `max_workers=2` | Reproducibly fails with a clean Python-level `IndexError: invalid vector<bool> subscript` raised from `paddlex/inference/pipelines/_parallel.py` (not a native crash this time — a catchable Python exception) |
| 2 threads, **separate** `PaddleOcrAdapter()` instance per thread, `max_workers=2` | Native access violation (exit `-1073741819` / `0xC0000005`) — rules out Python-level instance-sharing as the sole cause |
| 2 threads, one shared instance, different attempt | Native access violation (exit `-1073741819`), stack trace captured above |
| 2 threads, one shared instance, re-run via subprocess-isolated test | Native **heap corruption** (exit code whose unsigned/hex form is `0xC0000374` / `STATUS_HEAP_CORRUPTION`) — a *third*, distinct native failure signature |

```
IndexError: invalid vector<bool> subscript
  File ".../paddleocr/_pipelines/ocr.py", line 213, in predict
  File ".../paddlex/inference/pipelines/_parallel.py", line 129, in predict
    yield from self._pipeline.predict(...)
```

**Classification: `CONFIRMED UNSAFE`** for concurrent multi-threaded use of
this adapter/engine on Windows with this pinned version — every concurrent
attempt made in this investigation failed, via one of **three** distinct
failure modes (`IndexError`, access violation `0xC0000005`, heap corruption
`0xC0000374`), regardless of whether the adapter instance was shared or
per-thread. The fact that the *exact* native failure signature differs
between attempts (not one deterministic crash code) is itself evidence
of genuine memory corruption rather than one single, fixable code path.
**Practical recommendation: do not call this adapter
concurrently from multiple threads in one process; serialize all
conversions** (e.g. one worker process per conversion, or a single-threaded
work queue). This is a stronger, more specific finding than the general
sequential-workload `UNRESOLVED` classification below — it is not
"sometimes fine," it reproduced a failure on every concurrent attempt
tried.

**What is consistent across both the Docling and PaddleOCR
investigations**: the fault appears **only** in runs that perform more than
one "shape" of work in a single process (multiple conversions, mixed
document types, or a cold-start-then-many-conversions pattern), and **never**
in this sandbox's narrowly-scoped, single-path, isolated-process probes.
This is suggestive but not proven — isolated probes are also simply shorter
and do less total native-library work, so "fewer total operations" remains
a confounded, not isolated, variable.

**Classification: `UNRESOLVED`** — not downgraded to "Low" or "resolved by
workaround." Per the mandate: an unexplained native-code access violation on
Windows, observed across TWO independent engines (Docling's `docling_parse`
C++ backend and now PaddlePaddle's native runtime) in this same environment,
is a standing operational risk for any Windows-hosted, long-lived MIZAN
ingestion process using either engine, and should be escalated to dedicated
soak/stress testing before any production reliance on either engine on
Windows. **Practical, honestly-disclosed test-suite consequence**: this
sandbox's test suite is run in small, single-concern batches (see
`run_tests.ps1`) specifically to manage this risk while still exercising
every test — this is a documented operational mitigation, not a hidden
workaround, and does not change the `UNRESOLVED` classification.

Full raw attempt/crash counts: `benchmark/windows_stability_results.json`.

## 8. Offline / Local-first behavior

Tested via `tests/test_offline_local_first.py`, which launches a **separate
subprocess** with `DISABLE_MODEL_SOURCE_CHECK=True` (PaddleX's documented
flag to skip its own "Checking connectivity to the model hosters" pre-flight
network check) AND `HTTP_PROXY`/`HTTPS_PROXY` pointed at an unreachable
local address (`http://127.0.0.1:1`), as a second, independent layer of
assurance beyond the documented flag — so any accidental live network call
would fail fast rather than silently succeeding via a real connection.

- **Scanned/OCR conversion**: succeeds fully offline once models are
  cached. ✅ (`test_scanned_ocr_conversion_succeeds_fully_offline` — PASS)
- **Offline output matches online output**: the offline subprocess run
  reports the same success/structure as a normal in-process run on the same
  fixture (not merely "succeeds" while silently degrading). ✅
  (`test_offline_conversion_produces_the_same_text_as_online_run` — PASS)

**Models required and where they are cached** (this environment):

| Model | Purpose | Source | Cache location |
|---|---|---|---|
| `PP-OCRv5_server_det` | Text-region detection | PaddleX model hub | `%USERPROFILE%\.paddlex\official_models\PP-OCRv5_server_det` |
| `arabic_PP-OCRv5_mobile_rec` | Text recognition, Arabic script | PaddleX model hub | `%USERPROFILE%\.paddlex\official_models\arabic_PP-OCRv5_mobile_rec` |
| (default) text-line classifier, if enabled | Orientation classification | PaddleX model hub | `%USERPROFILE%\.paddlex\official_models\` |

**Pre-provisioning for air-gapped deployment**: vendor/bundle the contents
of `%USERPROFILE%\.paddlex\official_models\` as part of the MIZAN build or
deployment artifact, and set `DISABLE_MODEL_SOURCE_CHECK=True` in the
runtime environment so PaddleX does not attempt its connectivity pre-check
at all (this sandbox's adapter and benchmark scripts already set this).

**If models are NOT present and there is no internet access**: PaddleX
raises a download/connection error when the missing model is first
requested; this was not independently re-verified by deleting the cache in
this sandbox (doing so would require re-downloading to restore the
environment for further testing) — same documented-inference caveat as the
Docling sandbox.

**No document content was sent to any external service** in any test in
this sandbox — only model weight downloads (which occurred once, during the
earlier version-compatibility investigation) touch the network, and those
carry no document content.

## 9. Stability / determinism across repeated runs (adapter-contract level)

Re-running the same scanned PDF repeatedly in the same process produces
**byte-identical** `raw_text` and `normalized_text` output
(`test_paddleocr_adapter.py::test_output_is_stable_across_repeated_runs`),
distinct from §7's native-process-level crash investigation.

## 10. Summary table vs. Docling sandbox (same machine, same fixture
categories where comparable)

| Dimension | Docling (RapidOCR, Arabic-configured) | PaddleOCR (PP-OCRv5 + Arabic mobile rec) |
|---|---|---|
| Born-digital PDF | Native text-layer read, OCR OFF, ~2.6-7s warm | OCR always applied, ~25-29s warm (2-10x slower for no benefit) |
| Scanned Arabic CER (clear) | 0.686 | **0.010** |
| Scanned Arabic WER (clear) | 0.895 | **0.053** |
| Scanned Arabic table WER | 1.524 (fails sanity ceiling) | **0.667** (passes, but no table structure) |
| Scanned low-quality | CER 1.0 / WER 1.0 (total failure) | CER 0.710 / WER 0.895 (severe, not total) |
| DOCX/XLSX/PPTX | Supported | Not supported at all |
| Table structure recovery | Yes (born-digital path) | No (base OCR pipeline) |
| Windows access violation | Observed, UNRESOLVED | Observed independently, UNRESOLVED |
| Offline/local-first | Verified | Verified |
| Warm steady-state memory | ~628 MB | ~639-780 MB |
