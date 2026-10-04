# PaddleOCR vs. MIZAN Needs — Comparison and Final Decision

This document compares PaddleOCR's **measured** (not assumed) behavior
against MIZAN's requirements, based on the sandbox prototype in this folder
(`sandboxes/paddleocr/`) and the results in `benchmark/RESULTS.md`. It is
built the same way, against the same real, merged MIZAN Core Contracts
(`contracts/mizan_contracts/`: Canonical/Provenance/Identity/Stable-Locator
v1) as the Docling sandbox (PR #2), via an independent `mizan_bridge.py`
with zero dependency on `sandboxes/docling/`.

## MIZAN's evidence pipeline — and where this sandbox sits in it

```
SOURCE -> RAW EXTRACTION -> NORMALIZATION -> INTERPRETATION -> VERIFICATION -> ACCEPTED FACT
          \_______________________________/
             this adapter's scope only
```

`PaddleOcrAdapter` and `NormalizedDocumentResult`/`AdapterDocumentResult`
cover exactly **RAW EXTRACTION** (`raw_text`, exactly what PaddleOCR
returned, concatenated in its own detection order) and **NORMALIZATION**
(`normalized_text`, after Unicode NFKC, computed inside the adapter itself —
see `tests/test_paddleocr_adapter.py::test_normalize_text_function_runs_real_nfkc_not_a_test_only_helper`).
Neither PaddleOCR nor this adapter/bridge performs or is permitted to perform
INTERPRETATION, VERIFICATION, or produce an ACCEPTED FACT — there is no
`to_fact`/`AcceptedFact`/`status`/`verified` attribute anywhere in
`adapter.py` or `mizan_bridge.py`
(`tests/test_mizan_contract_bridge.py::test_bridge_output_has_no_fact_or_accepted_fact_attribute`).

## What PaddleOCR adds

- **Materially better Arabic OCR accuracy than Docling's RapidOCR
  configuration**, on the same shared fixture: on `scanned_arabic_table`,
  PaddleOCR measured **WER=0.667** vs Docling's documented **WER=1.524** —
  a real, directly comparable improvement (`benchmark/RESULTS.md` §3,
  `tests/test_scanned_ocr_quality.py::test_scanned_arabic_table_wer_vs_docling_baseline`).
  Across all 10 synthetic scanned-Arabic fixtures tested, CER ranges
  0.010–0.710 and WER ranges 0.053–0.895 (full table in
  `benchmark/ocr_quality_results.json`), outperforming Docling's documented
  CER 36–100% / WER 43–152% range on its comparable fixture set.
- First-class, purpose-built Arabic recognition model
  (`arabic_PP-OCRv5_mobile_rec`) that works correctly without the
  language-misconfiguration failure mode Docling's default RapidOCR
  exhibited (silently defaulting to a non-Arabic language).
- A real `page_index` for every recognized line (rasterizes and OCRs each
  PDF page independently), giving reliable multi-page structure that the
  bridge uses directly — a small capability advantage over engines that only
  report flattened text.
- Clean failure handling for missing/corrupted/unsupported files: reported
  as a structured failure (`success=False`, populated `errors`), not a
  process crash (`tests/test_paddleocr_adapter.py::test_missing_file_is_reported_as_failure_not_an_exception`,
  `test_corrupted_pdf_does_not_crash_the_pipeline`, `test_unsupported_extension_does_not_crash`).
- Deterministic `raw_text`/`normalized_text` output across repeated runs on
  the same input at the adapter-contract level
  (`tests/test_scanned_ocr_quality.py::test_output_is_stable_across_repeated_runs_on_same_fixture`),
  independent of the separate native-stability question below.
- Fully offline/local-first once models are cached — no document content
  sent to any external service (`tests/test_offline_local_first.py`, both
  passed; `benchmark/RESULTS.md` §8).

## What PaddleOCR duplicates from existing MIZAN capability

**`NEEDS COMPARISON WITH CURRENT MIZAN INGESTION`**

This sandbox, like the Docling sandbox before it, never examined MIZAN's
actual current ingestion code, so it has no basis to assert overlap or
non-overlap with any existing MIZAN capability. A real comparison requires
reading MIZAN's existing document-ingestion implementation (if one exists)
and comparing it feature-by-feature against PaddleOCR's measured behavior
above — this has not been done. Until that comparison exists, assume unknown
overlap, not zero overlap, and not "new capability" merely because it exists
in PaddleOCR.

## What PaddleOCR does NOT solve

- **No OCR-off path for born-digital PDFs.** Unlike Docling, PaddleOCR's OCR
  pipeline has no text-layer reader: it always rasterizes every page and
  always runs OCR, even for a perfect-text-layer PDF. Measured cost: ~22–29s
  per document (warm) vs Docling's ~2.6–7s for the same born-digital case
  (`benchmark/RESULTS.md` §2, §6). This is an architectural gap, not a bug.
- **No DOCX/XLSX/PPTX support at all** — PaddleOCR's OCR pipeline is
  image/PDF-only. Recorded explicitly as `NOT SUPPORTED`, not worked around
  (`benchmark/RESULTS.md` §1).
- **No table structure recovery.** PaddleOCR's plain OCR pipeline returns a
  flat, ordered list of recognized text lines — individual cell *values* are
  correctly recognized, but there is no row/column/cell structure
  reconstruction (`tables=[]` always). PaddleOCR separately ships a
  layout+table pipeline (`PPStructureV3`) that was explicitly **NOT
  evaluated** in this sandbox (different model footprint/scope) — recorded
  as an open question, not silently assumed equivalent
  (`benchmark/RESULTS.md` §5).
- **Concurrency.** See Risks below — this is a hard functional gap, not a
  performance one.
- **Arabic-aware NLP.** PaddleOCR extracts text; it does not perform Arabic
  legal NER, clause extraction, or entity resolution. MIZAN still owns all
  of that.
- **Soak-tested Windows stability.** Both the general sequential-workload
  finding and the concurrency finding below remain open, not cleared.

## Risks

| Risk | Severity | Evidence / reasoning |
|---|---|---|
| Concurrent multi-threaded use of the adapter | **High — CONFIRMED UNSAFE** | Reproduces a failure on **every** attempt made (not intermittent): a clean Python `IndexError: invalid vector<bool> subscript`, a native access violation (`0xC0000005`), or native heap corruption (`0xC0000374`) — regardless of shared vs. per-thread adapter instances. See `benchmark/RESULTS.md` §7a. Practical mitigation: never call concurrently; serialize all conversions. |
| General sequential-workload native crash (Windows) | **Unresolved** (explicitly not downgraded to Low) | Reproducible native access violation (`0xC0000005`), intermittent, correlated with cumulative native call volume in one long-lived process rather than any single isolated input/order factor. Reproduced again during this session's own grouped test run (`windows_stability_results.json`'s `grouped_pytest_run_ocr_routing_combined` entry) and during the standalone `benchmark_cold_warm.py` combined run (2/2). Root cause not isolated (PaddleOCR / PaddleX / PaddlePaddle native runtime / pytest interaction all remain plausible). |
| No OCR-off path doubles-or-worse per-document latency for the common born-digital case vs. Docling | Medium-High | Measured directly: ~22–29s (PaddleOCR, always-OCR) vs. ~2.6–7s (Docling, OCR-off) for the same born-digital fixture, `benchmark/RESULTS.md` §6 |
| No table structure recovery | Medium | Confirmed gap vs. Docling's born-digital table extraction; `PPStructureV3` (the layout/table pipeline) was not evaluated, so this gap's fixability within the PaddleOCR ecosystem is unknown |
| No DOCX/XLSX/PPTX support | Medium | Confirmed gap vs. Docling, which supports all three; any MIZAN deployment needing non-PDF/image ingestion cannot use PaddleOCR alone |
| Strict version pinning required (`paddleocr==3.3.3`+`paddlepaddle==3.2.2`) | Medium | Newer default-pip versions crash or raise with 3 distinct, confirmed failure modes on this machine (see `adapter.py` "Version pinning" docstring) — this is a narrow, fragile compatibility window to maintain long-term |
| First-run network dependency conflicts with strict local-first/air-gapped deployment | Medium | Confirmed: `PP-OCRv5_server_det` + `arabic_PP-OCRv5_mobile_rec` models required from PaddleX's hoster; offline mode works once cached (verified), but cache must be pre-provisioned; `DISABLE_MODEL_SOURCE_CHECK=True` needed to skip a noisy (non-fatal) connectivity pre-flight check |
| Cold-start latency | Low-Medium | Measured ~11.7–12.8s cold start (model load), separated cleanly from warm-run cost; see `benchmark/RESULTS.md` §6 |
| Upstream project changes direction or slows down | Low-Medium | Actively maintained (PaddlePaddle/PaddleOCR, Baidu-backed), but the narrow working-version window above suggests nontrivial breakage risk even within normal upstream releases |

## Windows / local-first impact

- Runs successfully on Windows for all single-conversion and bounded
  sequential-workload tests in this sandbox (73 tests passed across all
  files when run in appropriately-sized, isolated groups — see "Tests" below).
- Two distinct, honestly-classified native-stability findings remain open —
  see Risks above and `benchmark/RESULTS.md` §7/§7a. The concurrency finding
  in particular (`CONFIRMED UNSAFE`) is a hard constraint: this adapter must
  never be called concurrently from multiple threads in one process.
- Confirmed to work fully offline once models are cached
  (`tests/test_offline_local_first.py`, 2/2 passed) — a positive, verified
  finding, not an assumption.
- Still requires a one-time internet-connected provisioning step (or
  vendored model weights) before first use; a genuinely air-gapped MIZAN
  deployment must pre-provision `%USERPROFILE%\.paddlex\official_models\`
  with the exact two models documented in `benchmark/RESULTS.md` §8.

## Privacy impact

- No document content leaves the machine during conversion (verified by the
  offline test, which demonstrates identical conversion output with network
  access unavailable).
- Only model weight downloads touch the network, and only during
  provisioning, not per-document.

## Dependency footprint

- Heavier than a lightweight library: `paddlepaddle` (full ML inference
  runtime, native C++ core) + `paddleocr` (built on `paddlex`'s pipeline
  framework). Hundreds of MB on disk for the runtime plus the two cached
  models. A narrower, more fragile compatible-version window than Docling's
  dependency set (3 confirmed-broken alternate version combinations
  encountered during this sandbox's own setup — see `adapter.py` docstring).

## Can it be isolated behind an adapter?

- **Yes, and this sandbox proves it concretely**, using the same pattern
  validated by the Docling sandbox. `adapter.py` is the only module that
  imports `paddleocr`/`paddlex`/`paddle`; `mizan_bridge.py` imports FROM
  `mizan_contracts` and FROM `adapter`, never the reverse; nothing in
  `contracts/mizan_contracts/` knows about PaddleOCR or this sandbox. If
  PaddleOCR were replaced, only `adapter.py` + `mizan_bridge.py` would need
  to change, and the MIZAN-owned Identity/Stable-Locator/Provenance
  contracts would be untouched.

## What happens if the project stops being maintained?

- Because the integration is fully isolated behind `PaddleOcrAdapter`, the
  blast radius of PaddleOCR being abandoned is contained to reimplementing
  one adapter module against the same `AdapterDocumentResult` contract.
- The narrow, already-fragile compatible-version window (3 other version
  combinations already broken on this machine) means a MIZAN deployment
  depending on PaddleOCR is more exposed than average to being stuck on an
  unmaintained/pinned version if the upstream project stalls — a stronger
  caution than the equivalent Docling finding.

## MIZAN Core Contract Gate

This sandbox was built directly against the real, merged Core Contracts
(`contracts/mizan_contracts/`: canonical_v1, provenance_v1, identity_v1,
stable_locator_v1) from the start — not against placeholders — via
`mizan_bridge.py`:

```
MIZAN CONTRACT
        ^
     ADAPTER  (adapter.py + mizan_bridge.py)
        ^
    PADDLEOCR
```

| Criterion | Result | Evidence |
|---|---|---|
| AC-P01 Core Contracts loaded from `main` | PASS | `mizan_bridge.py` imports `contracts/mizan_contracts` directly from the repo checkout on `main`; no vendored copy in `.venv` |
| AC-P02 Adapter respects Canonical v1 | PASS | `bridge_to_mizan()` constructs real `canonical_v1.SourceArtifact/Document/DocumentVersion/Page/Block/Span/RawObservation` instances; validated by `tests/test_mizan_contract_bridge.py` |
| AC-P03 SHA-256 provenance complete | PASS | `adapter.sha256_of_file` computes the hash from file bytes before OCR runs; bridge validates it before use; absence/invalid shapes rejected (`test_missing_or_invalid_sha256_is_rejected`, 5 parametrized shapes: empty, too short, too long, non-hex, uppercase) |
| AC-P04 Identity owned by MIZAN | PASS | `document_id`/`source_artifact_id` are MIZAN-minted, never derived from PaddleOCR; `test_two_artifacts_can_point_to_same_document_without_merging` and `test_same_normalized_content_different_bytes_is_duplicate_candidate_only` prove no auto-merge |
| AC-P05 Stable Locator owned by MIZAN | PASS | `LocatorAllocator` issues locators from its own counters only, validated via `stable_locator_v1.validate_locator_component`; `test_engine_native_id_used_as_locator_is_rejected_by_bridge_guard` and `test_malformed_locator_rejected_at_contract_level` prove rejection of poisoned/malformed locators |
| AC-P06 raw_text preserved | PASS | `test_raw_text_is_preserved_separately_from_normalized_text`; raw/normalized are always distinct fields through both `adapter.py` and `mizan_bridge.py` |
| AC-P07 normalized_text is real NFKC, applied in the adapter | PASS | `test_normalize_text_function_runs_real_nfkc_not_a_test_only_helper` (adapter-level), `test_normalized_text_overwriting_raw_text_is_rejected` (bridge-level guard) |
| AC-P08 structural Observation→SHA-256 trace works | PASS | `test_reverse_traceability_structural_chain_succeeds`. Explicitly NOT an "Accepted Fact -> SHA-256" claim — verification layer does not exist in this sandbox |
| AC-P09 OCR routing recorded honestly (even though always-on) | PASS | `ocr_mode`/`ocr_reason`/`ocr_engine` recorded on every result; `tests/test_ocr_applied_always.py` proves the always-on behavior is explicit and tested, not hidden |
| AC-P10 engine dependency boundary clean | PASS | `mizan_bridge.py` imports FROM `mizan_contracts`, never the reverse; `contracts/mizan_contracts/` has zero PaddleOCR/PaddleX/PaddlePaddle imports |
| AC-P11 no Observation→AcceptedFact promotion | PASS | `test_bridge_output_has_no_fact_or_accepted_fact_attribute`: no `to_fact`/`status`/`verified`/`accepted` attribute anywhere on the bridged output |
| AC-P12 engine confidence is not treated as verification | PASS | `test_engine_confidence_is_not_a_verification_signal` |
| AC-P13 failed extraction never silently bridged | PASS | `test_failed_extraction_is_never_silently_bridged` |
| AC-P14 multi-page content split correctly | PASS | `test_multi_page_content_is_split_across_distinct_page_entities` |
| AC-P15 Arabic OCR actually measured (CER/WER), not assumed from `success=True` | PASS | `benchmark/ocr_quality_results.json`, all 10 fixtures; `tests/test_scanned_ocr_quality.py` (32 tests) |
| AC-P16 comparison vs Docling baseline is real, not assumed | PASS | `test_scanned_arabic_table_wer_vs_docling_baseline` directly compares against Docling's documented, measured WER on the same shared fixture |
| AC-P17 sequential Windows stability investigated | **UNRESOLVED** (recorded honestly, not downgraded) | `tests/test_windows_stability.py`; `benchmark/windows_stability_results.json`'s `investigation_summary.classification_for_pinned_version` |
| AC-P18 concurrency Windows stability investigated | **CONFIRMED UNSAFE** (recorded honestly, not downgraded, not hidden) | Same file; `concurrency_classification` field; reproduced via 3 distinct native/Python failure modes across attempts |
| AC-P19 cold-start vs warm-run separated | PASS | `benchmark/benchmark_cold_warm.py` + `benchmark/cold_warm_results.json`; limitation (combined single-process run crashes, numbers obtained via per-path process isolation) documented, not hidden |
| AC-P20 offline/local-first verified | PASS | `tests/test_offline_local_first.py`, 2/2 passed |
| AC-P21 table structure gap recorded honestly, not faked | PASS | `benchmark/RESULTS.md` §5: `tables=[]` always, `PPStructureV3` explicitly out of scope, not silently assumed equivalent to Docling |
| AC-P22 no real/sensitive case data used anywhere in fixtures | PASS | All fixtures generated synthetically by `fixtures/generate_scanned_corpus.py`; no case files, no personal/legal data |

## Tests

Full test suite, run in appropriately-sized isolated groups per
`run_tests.ps1` (required due to both the sequential-UNRESOLVED and
concurrency-CONFIRMED-UNSAFE native-crash risks — see README.md):

| File | Passed | Failed | Skipped | Errors |
|---|---|---|---|---|
| `test_paddleocr_adapter.py` | 13 | 0 | 0 | 0 |
| `test_mizan_contract_bridge.py` | 17 | 0 | 0 | 0 |
| `test_ocr_applied_always.py` | 3 | 0 | 0 | 0 |
| `test_vector_pdf_capability.py` | 2 | 0 | 0 | 0 |
| `test_scanned_ocr_quality.py` | 32 | 0 | 0 | 0 |
| `test_windows_stability.py` | 4 | 0 | 0 | 0 |
| `test_offline_local_first.py` | 2 | 0 | 0 | 0 |
| **Total** | **73** | **0** | **0** | **0** |

All 73 tests pass with **zero skips** when each file/small-group is run as
its own isolated `pytest` subprocess. One real native crash was recorded
*during this session's own test running* when `test_ocr_applied_always.py`
and `test_vector_pdf_capability.py` were combined into a single pytest
subprocess (documented in `windows_stability_results.json`'s
`grouped_pytest_run_ocr_routing_combined` entry) — this is itself further,
unplanned evidence supporting the sequential-workload `UNRESOLVED` finding
(not a new distinct bug), and `run_tests.ps1` runs these two files as
separate groups specifically because of it.

### Sandbox Capability Candidate vs. Approved MIZAN Production Capability

These are explicitly **not the same statement**:

- **Sandbox Capability Candidate: PASS.** The contract-integration layer
  (Canonical/Provenance/Identity/Stable-Locator) is real, tested, and
  adversarially validated against the actual merged Core Contracts, for the
  **scanned Arabic OCR** path, with measurably better accuracy than
  Docling's current OCR configuration.
- **Approved MIZAN Production Capability: NO.** Independent blockers prevent
  production approval regardless of contract-layer or OCR-quality success:
  1. Concurrency is **CONFIRMED UNSAFE** — a hard constraint, not a
     performance caveat.
  2. Sequential-workload native crash remains **UNRESOLVED**.
  3. No OCR-off path, no DOCX/XLSX/PPTX support, and no table structure
     recovery are confirmed functional gaps vs. MIZAN's likely full
     ingestion needs.

Any one of these is sufficient to withhold production approval.

## Final decision

### Decision: **CONNECT**

PaddleOCR is not adopted as a general-purpose ingestion engine (it cannot
replace Docling's broader format coverage), and it is not merged into the
MIZAN core today. It is classified **CONNECT**: a candidate adjacent
engine worth keeping available, isolated behind its own adapter, as a
**specialized, higher-accuracy Arabic-OCR path** that could be selectively
invoked (e.g. by a future routing layer) for scanned-Arabic documents
specifically — alongside, not instead of, Docling or MIZAN's existing
ingestion — once its two Windows-stability blockers are resolved and a
decision is made on table-structure recovery (`PPStructureV3`, not yet
evaluated).

### Why not REUSE
"Drop-in, ready for production" is not supported: concurrency is confirmed
unsafe, sequential stability is unresolved, and there is no OCR-off/
DOCX/XLSX/PPTX/table-structure coverage. REUSE would misrepresent the real,
measured state of this sandbox.

### Why not EXTEND
EXTEND (Docling's classification) implies the gaps are addressable by
building MIZAN-side wrappers/config around an otherwise-solid base (as was
true for Docling's OCR-routing and NFKC gaps). Here, the blocking gaps are
either upstream native-stability bugs this sandbox could not fix from the
adapter layer (concurrency, sequential crash) or fundamental pipeline
scope limits (no OCR-off path, no table structure, no non-PDF formats) that
an adapter cannot wrap around — these are harder, more structural
limitations than Docling's.

### Why not INSPIRE / REJECT
INSPIRE would understate PaddleOCR's real, working, measurably-better
Arabic OCR accuracy — a genuine, directly-usable capability once its
constraints are respected (serialized calls, isolated process). REJECT
would discard that real accuracy advantage over Docling's current OCR
configuration, which is the single most actionable finding in this sandbox.

## Suggested next steps (not performed in this sandbox)

1. Resolve or further bound the concurrency `CONFIRMED UNSAFE` finding —
   e.g. test whether a single long-lived worker process consuming a queue
   (no threads) avoids both failure modes, which would make "serialize all
   calls" operationally cheap rather than merely a constraint.
2. Investigate the sequential `UNRESOLVED` native-crash finding at
   meaningfully higher repetition than this sandbox's bounded probes, ideally
   with PaddlePaddle's own debug/diagnostic builds, before any production
   dependency on this pinned version on Windows.
3. Evaluate `PPStructureV3` (PaddleOCR's layout+table pipeline) specifically
   for Arabic table extraction, to determine whether the table-structure gap
   found here is fixable within the PaddleOCR ecosystem.
4. Compare against MIZAN's actual current document-ingestion implementation
   (if any) to resolve the "NEEDS COMPARISON" item above.
5. If concurrency and sequential stability are resolved, re-evaluate whether
   a routing layer (Docling for born-digital + broad format coverage,
   PaddleOCR for scanned-Arabic) is worth the combined dependency footprint
   of running both engines in one MIZAN deployment.
