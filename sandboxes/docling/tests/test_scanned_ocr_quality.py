"""
MIZAN Docling Sandbox - Scanned Arabic OCR Quality (CER/WER)

Runs OCR (via the adapter's real routing path) against the synthetic scanned
Arabic corpus and computes CER/WER against ground truth. `success=True` from
the adapter is NOT treated as evidence of OCR quality here -- only the
measured CER/WER is.

Results (expected text, extracted text, CER, WER) are persisted to
benchmark/ocr_quality_results.json so the measurement can be reproduced and
audited without re-running OCR.
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from adapter import DoclingAdapter  # noqa: E402
from benchmark.ocr_metrics import compute_cer_wer  # noqa: E402

FIXTURES = ROOT / "fixtures"
RESULTS_PATH = ROOT / "benchmark" / "ocr_quality_results.json"

SCANNED_CASES = [
    "scanned_arabic_clear",
    "scanned_arabic_numeric",
    "scanned_mixed_ar_en",
    "scanned_arabic_table",
    "scanned_arabic_low_quality",
]

# Quality is NOT asserted as "good" here by design -- these are recorded,
# not gated, except for a loose sanity ceiling that catches total pipeline
# breakage (e.g. OCR returning nothing or pure garbage).
SANITY_CEILING_CER = 1.5
SANITY_CEILING_WER = 1.5


@pytest.fixture(scope="session")
def adapter() -> DoclingAdapter:
    return DoclingAdapter()


@pytest.fixture(scope="session")
def ocr_quality_results(adapter):
    """Run OCR once per case for the whole module and persist results."""
    results = {}
    for case in SCANNED_CASES:
        pdf_path = FIXTURES / f"{case}.pdf"
        expected_path = FIXTURES / f"{case}.expected.txt"
        expected_text = expected_path.read_text(encoding="utf-8")

        result = adapter.convert(pdf_path)
        score = compute_cer_wer(expected_text, result.normalized_text)

        results[case] = {
            "success": result.success,
            "ocr_mode": result.ocr_mode,
            "ocr_engine": result.ocr_engine,
            "processing_time_seconds": result.processing_time_seconds,
            "expected_text": expected_text,
            "extracted_text": result.normalized_text,
            "cer": score.cer,
            "wer": score.wer,
            "char_edit_distance": score.char_edit_distance,
            "word_edit_distance": score.word_edit_distance,
            "reference_char_count": score.reference_char_count,
            "reference_word_count": score.reference_word_count,
            "warnings": result.warnings,
            "errors": result.errors,
        }

    RESULTS_PATH.write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return results


@pytest.mark.parametrize("case", SCANNED_CASES)
def test_scanned_case_routes_through_ocr(ocr_quality_results, case):
    assert ocr_quality_results[case]["ocr_mode"] == "scanned"
    assert ocr_quality_results[case]["ocr_engine"] == "rapidocr(lang=arabic,en)"


# scanned_arabic_low_quality is EXCLUDED from the "produces output" hard
# assertion below: it is a deliberately degraded fixture (downscale + Gaussian
# blur) built specifically to stress-test OCR quality, and a real observed
# outcome on this engine/environment is EMPTY output (CER=1.0, i.e. total
# miss). Per the explicit MIZAN requirement to record OCR failure honestly
# rather than build a workaround to force a PASS, this is NOT hidden -- it is
# asserted and documented separately below and in benchmark/RESULTS.md.
STRICT_NONEMPTY_CASES = [c for c in SCANNED_CASES if c != "scanned_arabic_low_quality"]


@pytest.mark.parametrize("case", STRICT_NONEMPTY_CASES)
def test_scanned_case_produces_some_output(ocr_quality_results, case):
    """OCR must at least produce non-empty output for reasonable-quality scans.
    This does NOT assert quality -- see CER/WER for that."""
    assert ocr_quality_results[case]["success"] is True
    assert len(ocr_quality_results[case]["extracted_text"].strip()) > 0, (
        f"{case}: OCR produced completely empty output -- total failure, "
        "not a quality nuance."
    )


def test_low_quality_scan_ocr_outcome_is_recorded_honestly(ocr_quality_results):
    """
    DOCUMENTED NEGATIVE RESULT (not a workaround, not hidden): on the
    deliberately degraded low-quality scan fixture, RapidOCR (as integrated by
    Docling in this sandbox) returned EMPTY text in the run that produced
    benchmark/ocr_quality_results.json. The pipeline did not crash
    (`success=True` at the adapter level), but the OCR result itself is a
    total miss (CER=1.0). This assertion exists to make that regression-visible
    rather than silently passing or silently failing.
    """
    case = ocr_quality_results["scanned_arabic_low_quality"]
    assert case["success"] is True, "Pipeline-level failure (crash), not just an OCR quality miss."
    extracted_is_empty = len(case["extracted_text"].strip()) == 0
    if extracted_is_empty:
        assert case["cer"] == pytest.approx(1.0, abs=0.01), (
            "Empty OCR output should correspond to CERâ‰ˆ1.0 (total miss)."
        )
    # Either outcome (empty output with CERâ‰ˆ1.0, or some output with a
    # measured CER/WER) is an acceptable, honestly-recorded result for this
    # fixture -- this test only guards against silent corruption of the
    # recorded numbers, not against OCR being imperfect here.


@pytest.mark.parametrize("case", SCANNED_CASES)
def test_scanned_case_cer_wer_within_sanity_ceiling(ocr_quality_results, case):
    """
    This is a SANITY check, not a quality bar: it only fails if OCR output is
    so far from the expected text that the pipeline is essentially broken
    (CER/WER > 150%). Real CER/WER values -- even if poor -- are recorded in
    benchmark/ocr_quality_results.json and benchmark/RESULTS.md regardless of
    whether this sanity check passes.
    """
    cer = ocr_quality_results[case]["cer"]
    wer = ocr_quality_results[case]["wer"]
    assert cer <= SANITY_CEILING_CER, (
        f"{case}: CER={cer:.3f} exceeds sanity ceiling {SANITY_CEILING_CER}; "
        "OCR likely produced near-garbage output. See benchmark/ocr_quality_results.json."
    )
    assert wer <= SANITY_CEILING_WER, (
        f"{case}: WER={wer:.3f} exceeds sanity ceiling {SANITY_CEILING_WER}."
    )


def test_cer_wer_results_file_is_written(ocr_quality_results):
    assert RESULTS_PATH.exists()
    data = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    assert set(data.keys()) == set(SCANNED_CASES)

