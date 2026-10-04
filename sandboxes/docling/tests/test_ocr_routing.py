"""
MIZAN Docling Sandbox - OCR Routing Tests

Proves the OCR routing logic in adapter.py is REAL (not just described in
README): born-digital PDFs skip OCR, scanned PDFs run OCR, ambiguous PDFs run
OCR with an explicit warning, and the decision is recorded in the result.
"""
from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from adapter import DoclingAdapter  # noqa: E402

FIXTURES = pathlib.Path(__file__).resolve().parents[1] / "fixtures"


@pytest.fixture(scope="session")
def adapter() -> DoclingAdapter:
    return DoclingAdapter()


def test_born_digital_pdf_routes_ocr_off(adapter):
    result = adapter.convert(FIXTURES / "sample_plain_text.pdf")
    assert result.success is True
    assert result.ocr_mode == "born_digital"
    assert result.ocr_engine == "none"
    assert "chars/page" in result.ocr_reason


def test_born_digital_pdf_is_fast_without_ocr(adapter):
    """Regression tripwire for the routing's whole purpose: a born-digital PDF
    should complete much faster than the ~36s observed for the forced-OCR
    default pipeline. See benchmark/RESULTS.md cold/warm tables for full
    numbers; here we just assert it stays well under the no-routing baseline."""
    result = adapter.convert(FIXTURES / "sample_plain_text.pdf")
    assert result.ocr_mode == "born_digital"
    assert result.processing_time_seconds < 30, (
        f"born_digital OCR-off conversion took {result.processing_time_seconds:.1f}s; "
        "expected well under the ~36s forced-OCR baseline."
    )


def test_scanned_pdf_routes_ocr_on(adapter):
    result = adapter.convert(FIXTURES / "scanned_arabic_clear.pdf")
    assert result.success is True
    assert result.ocr_mode == "scanned"
    assert result.ocr_engine == "rapidocr(lang=arabic,en)"
    assert "No extractable text layer" in result.ocr_reason


def test_scanned_pdf_actually_extracts_text_via_ocr(adapter):
    """Proves OCR is not just "turned on" in name -- it must actually recover
    readable text from an image-only PDF with zero text layer."""
    result = adapter.convert(FIXTURES / "scanned_arabic_clear.pdf")
    assert result.success is True
    assert len(result.normalized_text.strip()) > 0, (
        "Scanned PDF produced no text at all; OCR engine did not run or failed silently."
    )


def test_ocr_decision_is_recorded_on_every_pdf_result(adapter):
    for fixture_name in ["sample_plain_text.pdf", "scanned_arabic_clear.pdf"]:
        result = adapter.convert(FIXTURES / fixture_name)
        assert result.ocr_mode in ("born_digital", "scanned", "ambiguous", "unknown")
        assert result.ocr_reason != ""
        assert result.ocr_engine in ("none", "rapidocr(lang=arabic,en)")


def test_non_pdf_formats_mark_ocr_routing_not_applicable(adapter):
    result = adapter.convert(FIXTURES / "sample.docx")
    assert result.ocr_mode == "not_applicable"
    assert result.ocr_engine == "none"


def test_ambiguous_pdf_routes_ocr_on_with_warning(adapter, tmp_path):
    """
    Construct a synthetic 'ambiguous' PDF: a real text layer exists (so it is
    not classified as fully scanned) but it is far too sparse to be trustworthy
    (well below MIN_CHARS_PER_PAGE_BORN_DIGITAL). The adapter must still run
    OCR as a safe fallback AND attach an explicit warning.
    """
    from reportlab.pdfgen import canvas as rl_canvas

    ambiguous_pdf = tmp_path / "ambiguous.pdf"
    c = rl_canvas.Canvas(str(ambiguous_pdf), pagesize=(612, 792))
    # Deliberately sparse: a handful of characters on an otherwise-blank page,
    # simulating a lightly-annotated scan or a stamp/signature-only page.
    c.drawString(72, 700, "OK")
    c.showPage()
    c.save()

    result = adapter.convert(ambiguous_pdf)
    assert result.ocr_mode == "ambiguous", f"Expected ambiguous routing, got {result.ocr_mode} ({result.ocr_reason})"
    assert result.ocr_engine == "rapidocr(lang=arabic,en)"
    assert any("AMBIGUOUS PDF" in w for w in result.warnings), (
        "Ambiguous PDFs must produce an explicit warning, not a silent OCR-on decision."
    )

