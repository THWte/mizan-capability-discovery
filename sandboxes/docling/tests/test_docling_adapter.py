"""
MIZAN Docling Sandbox - Automated Test Suite (core adapter behavior)

These tests measure actual extraction quality against synthetic fixtures. They do
NOT use any real case data. Run with:

    .venv\\Scripts\\python.exe -m pytest tests -v
"""
from __future__ import annotations

import pathlib
import sys
import unicodedata

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from adapter import DoclingAdapter  # noqa: E402

FIXTURES = pathlib.Path(__file__).resolve().parents[1] / "fixtures"

ORIGINAL_ARABIC_LINES = [
    "هذا مستند تجريبي اصطناعي وليس ملف قضية حقيقي",
    "العنوان: مذكرة تجريبية خيالية",
    "الطرف الأول: شركة الاختبار الوهمية",
    "الطرف الثاني: مؤسسة النموذج الوهمية",
    "البند الأول: هذا نص تجريبي فقط لاختبار استخراج النص العربي",
    "البند الثاني: يجب أن يحافظ الترتيب على اتجاه الكتابة من اليمين لليسار",
]


@pytest.fixture(scope="session")
def adapter() -> DoclingAdapter:
    return DoclingAdapter()


# ---------------------------------------------------------------------------
# Basic read / failure handling
# ---------------------------------------------------------------------------

def test_plain_text_pdf_reads_successfully(adapter):
    result = adapter.convert(FIXTURES / "sample_plain_text.pdf")
    assert result.success is True
    assert result.errors == []


def test_plain_text_pdf_preserves_core_text(adapter):
    result = adapter.convert(FIXTURES / "sample_plain_text.pdf")
    assert "SYNTHETIC TEST DOCUMENT" in result.normalized_text
    assert "Section 1: Purpose" in result.normalized_text
    assert "Section 2: Fictional Parties" in result.normalized_text
    assert "Section 3: Fictional Terms" in result.normalized_text


def test_docx_reads_successfully_and_preserves_headings(adapter):
    result = adapter.convert(FIXTURES / "sample.docx")
    assert result.success is True
    assert "SYNTHETIC TEST DOCUMENT" in result.normalized_text
    assert "Section 1: Fictional Background" in result.normalized_text
    assert "Section 2: Fictional Findings" in result.normalized_text


def test_xlsx_reads_successfully(adapter):
    result = adapter.convert(FIXTURES / "sample.xlsx")
    assert result.success is True
    assert "FX-0001" in result.normalized_text
    assert "FX-0002" in result.normalized_text


def test_pptx_reads_successfully(adapter):
    result = adapter.convert(FIXTURES / "sample.pptx")
    assert result.success is True
    assert "SYNTHETIC TEST DECK" in result.normalized_text
    assert "Fictional bullet one" in result.normalized_text


def test_corrupted_pdf_fails_without_crashing_pipeline(adapter):
    result = adapter.convert(FIXTURES / "corrupted.pdf")
    assert result.success is False
    assert len(result.errors) > 0
    # Must not raise -- the adapter must contain the failure.


def test_unsupported_extension_fails_cleanly(adapter):
    result = adapter.convert(FIXTURES / "unsupported.xyz")
    assert result.success is False
    assert len(result.errors) > 0


def test_missing_file_fails_cleanly(adapter):
    result = adapter.convert(FIXTURES / "does_not_exist.pdf")
    assert result.success is False
    assert "does not exist" in result.errors[0]


# ---------------------------------------------------------------------------
# Table extraction
# ---------------------------------------------------------------------------

def test_pdf_table_extraction_recovers_expected_cells(adapter):
    result = adapter.convert(FIXTURES / "sample_with_tables.pdf")
    assert result.success is True
    assert len(result.tables) == 1
    flat = [cell for row in result.tables[0].rows for cell in row]
    assert any("EX-001" in cell for cell in flat)
    assert any("Accepted" in cell for cell in flat)
    assert any("EX-004" in cell for cell in flat)


def test_docx_table_extraction_recovers_expected_cells(adapter):
    result = adapter.convert(FIXTURES / "sample.docx")
    assert len(result.tables) >= 1
    flat = [cell for row in result.tables[0].rows for cell in row]
    assert any("Row 1" in cell for cell in flat)
    assert any("100" in cell for cell in flat)


# ---------------------------------------------------------------------------
# Content ordering
# ---------------------------------------------------------------------------

def test_plain_text_pdf_preserves_section_order(adapter):
    result = adapter.convert(FIXTURES / "sample_plain_text.pdf")
    text = result.normalized_text
    i1 = text.find("Section 1: Purpose")
    i2 = text.find("Section 2: Fictional Parties")
    i3 = text.find("Section 3: Fictional Terms")
    assert i1 < i2 < i3, "Sections were not preserved in original document order"


# ---------------------------------------------------------------------------
# Raw vs normalized text (NFKC applied INSIDE the adapter)
# ---------------------------------------------------------------------------

def test_arabic_pdf_reads_successfully(adapter):
    result = adapter.convert(FIXTURES / "sample_arabic.pdf")
    assert result.success is True
    assert len(result.normalized_text.strip()) > 0


def test_adapter_populates_both_raw_and_normalized_text(adapter):
    """The adapter contract requires BOTH fields to be present and non-empty
    for a successful conversion -- raw_text for provenance/audit, and
    normalized_text for downstream processing."""
    result = adapter.convert(FIXTURES / "sample_arabic.pdf")
    assert result.raw_text.strip() != ""
    assert result.normalized_text.strip() != ""


def test_adapter_performs_nfkc_normalization_itself_not_the_test(adapter):
    """
    KEY CONTRACT TEST: normalization must happen inside DoclingAdapter.convert(),
    not via a helper in this test file. We prove this by checking that
    `result.normalized_text` already equals unicodedata.normalize("NFKC",
    result.raw_text) -- i.e. the adapter has already done the work by the time
    the result reaches the caller. The test performs no normalization of its
    own on `result.normalized_text` anywhere below.
    """
    result = adapter.convert(FIXTURES / "sample_arabic.pdf")
    assert result.normalized_text == unicodedata.normalize("NFKC", result.raw_text), (
        "normalized_text must be exactly NFKC(raw_text); normalization is "
        "expected to be performed by the adapter itself."
    )


def test_normalized_text_matches_source_arabic_lines(adapter):
    """
    KEY FINDING: Docling extracts Arabic text generated by naive PDF writers as
    Unicode Presentation Forms (e.g. a presentation-form glyph for a word
    instead of plain Arabic letters), not plain Arabic letters. The raw
    extraction is therefore NOT directly usable as text for downstream Arabic
    NLP without normalization. The adapter's normalized_text recovers the
    exact original text and word order.
    """
    result = adapter.convert(FIXTURES / "sample_arabic.pdf")
    for line in ORIGINAL_ARABIC_LINES:
        assert line in result.normalized_text, f"Missing or altered after adapter NFKC: {line!r}"


def test_arabic_raw_output_is_presentation_forms_not_plain_letters(adapter):
    """Documents the defect: raw_text (as returned by Docling, before adapter
    normalization) does NOT match the source text directly. This test exists
    to make the limitation explicit and regression-visible, not to assert
    desirable behavior. raw_text must still be preserved for provenance/audit
    even though it is not directly usable downstream."""
    result = adapter.convert(FIXTURES / "sample_arabic.pdf")
    assert ORIGINAL_ARABIC_LINES[0] not in result.raw_text, (
        "Unexpected: raw Docling output already matches plain Arabic letters. "
        "If this now passes, Docling or the fixture generation changed -- update "
        "benchmark/RESULTS.md accordingly."
    )


def test_mixed_language_pdf_preserves_both_languages(adapter):
    result = adapter.convert(FIXTURES / "sample_mixed_ar_en.pdf")
    assert result.success is True
    text = result.normalized_text
    assert "SYNTHETIC MIXED-LANGUAGE DOCUMENT" in text
    assert "Section 1: English fictional clause." in text
    # At least one Arabic line should survive normalization in a mixed document.
    assert any(
        arabic_fragment in text
        for arabic_fragment in ["القسم الثاني", "بند تجريبي", "هذا بند خيالي"]
    ), "No recognizable Arabic fragment survived in the mixed-language document"


# ---------------------------------------------------------------------------
# Determinism / stability across repeated runs
# ---------------------------------------------------------------------------

def test_output_is_stable_across_repeated_runs(adapter):
    first = adapter.convert(FIXTURES / "sample_plain_text.pdf")
    second = adapter.convert(FIXTURES / "sample_plain_text.pdf")
    assert first.normalized_text == second.normalized_text
    assert first.raw_text == second.raw_text
    assert len(first.tables) == len(second.tables)


# ---------------------------------------------------------------------------
# Rough performance signal (not a strict benchmark, just a regression tripwire)
# ---------------------------------------------------------------------------

def test_processing_time_is_recorded_and_finite(adapter):
    result = adapter.convert(FIXTURES / "sample_plain_text.pdf")
    assert result.processing_time_seconds > 0
    assert result.processing_time_seconds < 300, (
        "Processing took unexpectedly long (>5 min) for a 1-page synthetic PDF; "
        "see benchmark/RESULTS.md for observed timings and why this matters for "
        "MIZAN's expected document volume."
    )


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------

def test_provenance_is_populated(adapter):
    result = adapter.convert(FIXTURES / "sample_plain_text.pdf")
    assert result.provenance.source_file_name == "sample_plain_text.pdf"
    assert result.provenance.engine == "docling"
    assert result.provenance.engine_version != "unknown"
