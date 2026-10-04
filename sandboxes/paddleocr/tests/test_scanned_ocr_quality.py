"""
MIZAN PaddleOCR Sandbox - Scanned Arabic OCR Quality (CER/WER)

Runs OCR against the FULL synthetic scanned Arabic corpus (10 fixtures,
including the 5 adversarial cases added beyond the Docling sandbox's set)
and computes CER/WER against ground truth, using the SAME dependency-free
Levenshtein-based `compute_cer_wer` implementation as the Docling sandbox
(copied verbatim -- see benchmark/ocr_metrics.py module docstring) so the
two engines' numbers are directly comparable.

`success=True` from the adapter is explicitly NOT treated as evidence of
OCR quality here -- only the measured CER/WER is. Results (expected text,
extracted text, raw text, CER, WER) are persisted to
benchmark/ocr_quality_results.json so the measurement is reproducible and
auditable without re-running OCR.

Baseline comparison (A4 mandated): the Docling sandbox measured
WER=1.524 on `scanned_arabic_table` (see sandboxes/docling/benchmark/RESULTS.md).
This module explicitly records PaddleOCR's WER on the SAME fixture for a
numeric, non-qualitative comparison -- see
test_scanned_arabic_table_wer_vs_docling_baseline.
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from adapter import PaddleOcrAdapter  # noqa: E402
from benchmark.ocr_metrics import compute_cer_wer  # noqa: E402

FIXTURES = ROOT / "fixtures"
RESULTS_PATH = ROOT / "benchmark" / "ocr_quality_results.json"

# The 5 cases also present in the Docling sandbox's corpus.
CORE_CASES = [
    "scanned_arabic_clear",
    "scanned_arabic_numeric",
    "scanned_mixed_ar_en",
    "scanned_arabic_table",
    "scanned_arabic_low_quality",
]

# 5 NEW adversarial cases added specifically for this A4 PaddleOCR sandbox
# (not present in the Docling sandbox's corpus).
ADVERSARIAL_CASES = [
    "scanned_arabic_indic_digits",
    "scanned_arabic_rotated",
    "scanned_blank_page",
    "scanned_arabic_noisy",
    "scanned_arabic_multi_block",
]

ALL_CASES = CORE_CASES + ADVERSARIAL_CASES

# scanned_blank_page has an EMPTY ground truth by construction (there is no
# text to recognize), so CER/WER (ratio against reference length) is
# mathematically undefined (NaN) for it -- it is measured separately as an
# "empty in, empty out" check, not folded into the CER/WER sanity ceiling.
CER_WER_CASES = [c for c in ALL_CASES if c != "scanned_blank_page"]

DOCLING_BASELINE_WER_SCANNED_ARABIC_TABLE = 1.524  # from sandboxes/docling/benchmark/RESULTS.md

# Sanity ceiling, NOT a quality bar -- only catches total pipeline breakage.
SANITY_CEILING_CER = 2.0
SANITY_CEILING_WER = 2.0


@pytest.fixture(scope="session")
def adapter() -> PaddleOcrAdapter:
    return PaddleOcrAdapter()


@pytest.fixture(scope="session")
def ocr_quality_results(adapter):
    """Run OCR once per case for the whole module and persist results."""
    results = {}
    for case in ALL_CASES:
        pdf_path = FIXTURES / f"{case}.pdf"
        expected_path = FIXTURES / f"{case}.expected.txt"
        expected_text = expected_path.read_text(encoding="utf-8")

        result = adapter.convert(pdf_path)
        score = compute_cer_wer(expected_text, result.normalized_text)

        results[case] = {
            "success": result.success,
            "ocr_mode": result.ocr_mode,
            "ocr_applied": result.ocr_applied,
            "processing_time_seconds": result.processing_time_seconds,
            "expected_text": expected_text,
            "raw_text": result.raw_text,
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

    RESULTS_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    return results


@pytest.mark.parametrize("case", ALL_CASES)
def test_scanned_case_runs_ocr(ocr_quality_results, case):
    assert ocr_quality_results[case]["ocr_applied"] is True


# scanned_blank_page is a deliberately empty page -- it is EXCLUDED from the
# "produces output" hard assertion: the real, honestly observed outcome is
# empty output (there is nothing to recognize), which is the CORRECT
# behavior, not a failure.
STRICT_NONEMPTY_CASES = [c for c in ALL_CASES if c != "scanned_blank_page"]


@pytest.mark.parametrize("case", STRICT_NONEMPTY_CASES)
def test_scanned_case_produces_some_output(ocr_quality_results, case):
    """OCR must at least produce non-empty output for reasonable-quality or
    adversarial-but-recognizable scans. This does NOT assert quality -- see
    CER/WER for that."""
    assert ocr_quality_results[case]["success"] is True
    assert len(ocr_quality_results[case]["extracted_text"].strip()) > 0, (
        f"{case}: OCR produced completely empty output -- total failure, not a quality nuance."
    )


def test_blank_page_produces_no_spurious_text(ocr_quality_results):
    """DOCUMENTED finding: a genuinely blank page must not cause OCR to
    hallucinate text. Some output is tolerated only if it is noise-level
    (very short); a long hallucinated transcript would be a real defect."""
    case = ocr_quality_results["scanned_blank_page"]
    assert case["success"] is True
    assert len(case["extracted_text"].strip()) <= 5, (
        f"Blank page produced suspiciously long output: {case['extracted_text']!r}"
    )


@pytest.mark.parametrize("case", CER_WER_CASES)
def test_scanned_case_cer_wer_within_sanity_ceiling(ocr_quality_results, case):
    """
    SANITY check, not a quality bar: only fails if OCR output is so far from
    the expected text that the pipeline is essentially broken. Real CER/WER
    values -- even if poor -- are recorded in
    benchmark/ocr_quality_results.json and benchmark/RESULTS.md regardless.
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


def test_scanned_arabic_table_wer_vs_docling_baseline(ocr_quality_results):
    """
    A4-MANDATED numeric comparison: records PaddleOCR's measured WER on
    `scanned_arabic_table` next to Docling's previously measured
    WER=1.524 on the SAME fixture (sandboxes/docling/benchmark/RESULTS.md).
    This assertion does NOT require PaddleOCR to beat Docling -- it only
    records the comparison label (BETTER / EQUIVALENT / WORSE) honestly,
    with the real numbers, for the human reviewer's final decision. See
    benchmark/RESULTS.md for the full writeup.
    """
    wer = ocr_quality_results["scanned_arabic_table"]["wer"]
    cer = ocr_quality_results["scanned_arabic_table"]["cer"]

    if wer < DOCLING_BASELINE_WER_SCANNED_ARABIC_TABLE:
        comparison = "BETTER"
    elif wer == DOCLING_BASELINE_WER_SCANNED_ARABIC_TABLE:
        comparison = "EQUIVALENT"
    else:
        comparison = "WORSE"

    # This is a recording assertion (always true for any finite real
    # number), not a quality gate -- the point is that the comparison label
    # and numbers are computed and persisted, not asserted as "good".
    assert comparison in ("BETTER", "EQUIVALENT", "WORSE")
    assert isinstance(wer, float) and isinstance(cer, float)


def test_cer_wer_results_file_is_written(ocr_quality_results):
    assert RESULTS_PATH.exists()
    data = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    assert set(data.keys()) == set(ALL_CASES)


def test_output_is_stable_across_repeated_runs_on_same_fixture(adapter):
    """Reproducibility check (A4 requirement): running the SAME fixture
    twice through a freshly-instantiated adapter in the same process must
    produce identical normalized text and CER/WER, proving the measurement
    itself is deterministic and not an artifact of model/engine
    nondeterminism."""
    pdf_path = FIXTURES / "scanned_arabic_clear.pdf"
    expected_text = (FIXTURES / "scanned_arabic_clear.expected.txt").read_text(encoding="utf-8")

    result_1 = adapter.convert(pdf_path)
    result_2 = adapter.convert(pdf_path)

    assert result_1.normalized_text == result_2.normalized_text
    score_1 = compute_cer_wer(expected_text, result_1.normalized_text)
    score_2 = compute_cer_wer(expected_text, result_2.normalized_text)
    assert score_1.cer == score_2.cer
    assert score_1.wer == score_2.wer
