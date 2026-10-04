"""
MIZAN PaddleOCR Sandbox - Raster/Scanned OCR-Applied Capability Tests

IMPORTANT -- Windows stability note (see benchmark/RESULTS.md "Windows
Access Violation Investigation"): this file intentionally converts ONLY
raster-image-based inputs (scanned PDF fixtures and a plain PNG). It must
NEVER be combined, in one `pytest` process, with
`tests/test_vector_pdf_capability.py` (which constructs reportlab
vector-text PDFs) -- mixing those two input "shapes" in a single process was
found to reproducibly (3/3 runs) crash the process with a native Windows
access violation (exit code -1073741819), independent of call order and of
whether the same adapter instance is reused. See `run_tests.ps1` for the
required two-group test invocation.

Scope: proves `ocr_applied` is unconditionally True on real scanned
documents too (complementing test_vector_pdf_capability.py's vector-text
coverage), and that the ocr_mode pre-check classification is still recorded
even though it is informational-only for this engine (see adapter.py module
docstring "Structural capability difference from Docling").
"""
from __future__ import annotations

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from adapter import PaddleOcrAdapter  # noqa: E402

FIXTURES = ROOT / "fixtures"


@pytest.fixture(scope="session")
def adapter() -> PaddleOcrAdapter:
    return PaddleOcrAdapter()


def test_scanned_pdf_runs_ocr_and_classification_matches(adapter):
    result = adapter.convert(FIXTURES / "scanned_arabic_clear.pdf")

    assert result.success is True
    assert result.ocr_mode == "scanned"
    assert result.ocr_applied is True


def test_ocr_decision_metadata_is_recorded_on_every_scanned_pdf_result(adapter):
    for fixture_name in ["scanned_arabic_clear.pdf", "scanned_arabic_table.pdf"]:
        result = adapter.convert(FIXTURES / fixture_name)
        assert result.ocr_mode in ("born_digital", "scanned", "ambiguous", "not_applicable", "unknown")
        assert result.ocr_reason != ""
        assert result.ocr_applied is True


def test_non_pdf_image_format_marks_routing_not_applicable_but_still_applies_ocr(adapter, tmp_path):
    """Images are the one input type for which the pre-check genuinely does
    not apply (it is pypdf-based), but PaddleOCR still runs OCR on them."""
    from PIL import Image

    png_path = tmp_path / "plain.png"
    Image.new("RGB", (200, 60), color="white").save(png_path)

    result = adapter.convert(png_path)

    assert result.ocr_mode == "not_applicable"
    assert result.ocr_applied is True
