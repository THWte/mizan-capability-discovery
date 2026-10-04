# MIZAN PaddleOCR Sandbox Prototype (A4)

Isolated, independent capability-discovery sandbox for **PaddleOCR**, built
the same way as `sandboxes/docling/` (Docling, PR #2): a throwaway prototype
to test whether PaddleOCR is worth REUSE / EXTEND / CONNECT / INSPIRE /
REJECT for MIZAN's Document Intelligence layer — **not** a production
integration, and **not** a replacement for any existing MIZAN capability.

This sandbox does **not** modify MIZAN Core Contracts, the Docling sandbox,
or any production code. It depends only on MIZAN Core Contracts v1
(`contracts/mizan_contracts`) as a read-only consumer, via `mizan_bridge.py`.

## Why PaddleOCR, and why separately from Docling

Docling's own sandbox (PR #2) found its OCR step (RapidOCR) weak on Arabic
(CER 36–100% / WER 43–152% across fixtures). PaddleOCR ships first-class
Arabic recognition models (`arabic_PP-OCRv5_mobile_rec`) and was evaluated
as a candidate specifically to see whether it closes that Arabic-OCR gap —
either as a REPLACEMENT OCR engine behind Docling, or as an independent
engine in its own right. See `benchmark/RESULTS.md` §10 for the head-to-head
comparison.

## Architecture: engine isolation

```
Document file
   |
   v
PaddleOcrAdapter.convert()      <-- adapter.py (ALL PaddleOCR-specific code lives here)
   |
   v
AdapterDocumentResult            <-- adapter.py's own dataclass, NOT a MIZAN contract type
   |
   v
to_mizan_contracts()              <-- mizan_bridge.py
   |
   v
mizan_contracts.canonical_v1 objects (SourceArtifact, Document, DocumentVersion,
Page, Block, Span, RawObservation, ...) + provenance_v1.Provenance
```

`adapter.py` has zero knowledge of MIZAN contracts. `mizan_bridge.py` has
zero PaddleOCR-specific logic — it only reads `AdapterDocumentResult` fields
and constructs MIZAN contract objects. If PaddleOCR were replaced, only
`adapter.py` changes; if MIZAN's contracts changed shape, only
`mizan_bridge.py` changes. Neither file lets PaddleOCR output become a MIZAN
`AcceptedFact` — see "Separation of concerns" below.

## Separation of concerns (mandatory MIZAN methodology)

```
SOURCE -> RAW EXTRACTION -> NORMALIZATION -> INTERPRETATION -> VERIFICATION -> ACCEPTED FACT
          \_______________________________/
               this adapter's scope only
```

- `raw_text`: exactly what PaddleOCR returned, concatenated in its own
  detection order, byte-for-byte unmodified. Preserved for provenance/audit.
- `normalized_text`: `raw_text` after Unicode NFKC normalization, applied
  **inside the adapter itself** (not a test-only helper) — this is what
  downstream MIZAN processing should read. See
  `tests/test_mizan_contract_bridge.py::test_normalization_happens_in_adapter_not_in_test_helper`.
- Neither `raw_text` nor `normalized_text` is ever promoted to a MIZAN
  `AcceptedFact` by this sandbox. There is no code path in `adapter.py` or
  `mizan_bridge.py` that constructs an `AcceptedFact`. Promotion to
  `AcceptedFact` is explicitly MIZAN's responsibility, outside this sandbox's
  scope — see `tests/test_mizan_contract_bridge.py`'s adversarial
  "direct promotion attempt" case.

## What this sandbox tested

- Format support: PDF (born-digital, scanned/image, ambiguous), and
  explicit "not supported" recording for anything else (PaddleOCR's OCR
  pipeline is image/PDF-only — no DOCX/XLSX/PPTX support at all; see
  `benchmark/RESULTS.md` §1).
- OCR routing: PaddleOCR has **no OCR-off path** — it always rasterizes and
  always runs OCR, even for a perfect-text-layer PDF. This is recorded as an
  architectural difference from Docling, not hidden or worked around
  (`adapter.py` module docstring, `benchmark/RESULTS.md` §2).
- Real CER/WER measurement across all 10 synthetic scanned-Arabic fixtures
  (`benchmark/ocr_quality_results.json`, `benchmark/RESULTS.md` §3).
- NFKC raw/normalized separation enforced inside the adapter.
- Table extraction: PaddleOCR's plain OCR pipeline has **no** table
  structure detection (flat line output only) — recorded as `NOT AVAILABLE`,
  not faked (`benchmark/RESULTS.md` §5).
- Cold-start vs warm-run benchmark, separated (`benchmark/benchmark_cold_warm.py`,
  `benchmark/cold_warm_results.json`, `benchmark/RESULTS.md` §6).
- Windows native-crash investigation — **two separate, honestly-classified
  findings**, see below.
- Offline/local-first behavior, once models are cached
  (`tests/test_offline_local_first.py`, `benchmark/RESULTS.md` §8).

## Windows stability: two distinct findings (read before using this adapter)

1. **Sequential workloads — `UNRESOLVED`, intermittent.** A real, reproducible
   native Windows access violation (exit `-1073741819` / `0xC0000005`) occurs
   in some multi-conversion, single-process runs. It does **not** correlate
   cleanly with any one isolated factor tested (input shape, call order,
   adapter reuse) — the best-supported partial theory is cumulative native
   call volume in one long-lived process. Root cause not isolated further
   (PaddleOCR / PaddleX / PaddlePaddle native runtime / pytest interaction
   all remain plausible). See `benchmark/RESULTS.md` §7 and
   `benchmark/windows_stability_results.json`.
2. **Concurrency — `CONFIRMED UNSAFE`, not merely intermittent.** Calling
   `.convert()` from 2 threads at once fails on **every** attempt made in
   this investigation, via one of **three** distinct failure modes: a clean
   Python `IndexError: invalid vector<bool> subscript`, a native access
   violation (`0xC0000005`), or native heap corruption (`0xC0000374`) —
   regardless of whether the adapter instance is shared or per-thread.
   **Practical recommendation: never call this adapter concurrently from
   multiple threads in one process; serialize all conversions.** See
   `benchmark/RESULTS.md` §7a.

Because of both findings, the test suite is intentionally run in small,
isolated groups rather than one single `pytest` invocation across every
file — see `run_tests.ps1` and "Running the tests" below.

## Running the tests

**Do not** run `pytest tests/` as one single invocation — the sequential
cumulative-volume finding above means a large combined run has a real
(if intermittent) chance of taking down the whole pytest process with a
native crash before all tests report results. Use the grouped script:

```powershell
cd sandboxes\paddleocr
.\.venv\Scripts\python.exe -m pip install -r requirements.txt   # first time only
.\run_tests.ps1
```

This runs each test file (or small file-group) as its own `pytest`
subprocess, reports pass/fail per group, and aggregates a final summary —
so a crash in one group does not hide the results of the others. See
`run_tests.ps1` for the exact grouping and rationale.

## Models and offline / local-first behavior

PaddleOCR (via PaddleX) downloads and caches models under
`%USERPROFILE%\.paddlex\official_models\` on first use:

- `PP-OCRv5_server_det` (text detector)
- `arabic_PP-OCRv5_mobile_rec` (Arabic text recognizer)

Set `DISABLE_MODEL_SOURCE_CHECK=True` in the environment to skip PaddleX's
"checking connectivity to the model hosters" network pre-flight check (this
check is not fatal without it, just noisy). Once models are cached, this
sandbox sends **no document content to any external service** — OCR runs
fully locally. See `tests/test_offline_local_first.py` and
`benchmark/RESULTS.md` §8 for the full pre-provisioning / no-internet
behavior writeup.

## Decision

See `COMPARISON_AND_DECISION.md` for the full AC-P01..AC-P22 acceptance
table, the comparison against both MIZAN's needs and the Docling sandbox,
and the final REUSE/EXTEND/CONNECT/INSPIRE/REJECT classification with
reasoning.

## Non-goals / explicit constraints honored by this sandbox

- Does not modify MIZAN Core, `contracts/`, or any production code.
- Does not modify or merge the Docling sandbox / PR #2.
- Uses only synthetic fixtures generated by `fixtures/generate_scanned_corpus.py`
  — no real case files, no personal or sensitive legal data.
- Does not treat installation success as capability success — every claim in
  `benchmark/RESULTS.md` is backed by an actual measured run.
- Does not merge this PR automatically.
