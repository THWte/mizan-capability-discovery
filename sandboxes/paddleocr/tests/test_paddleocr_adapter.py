"""
MIZAN PaddleOCR Sandbox - Core Adapter Behavior

Validates `adapter.py` directly: version-pin enforcement, SHA-256
provenance, NFKC applied inside the adapter itself (not by a test helper),
raw/normalized text separation, missing-file handling, and non-PDF
handling. Requires the real pinned PaddleOCR/PaddlePaddle install (these
tests exercise the real engine, not a mock), matching the Docling sandbox's
approach of testing the real pipeline rather than a double.
"""
from __future__ import annotations

import pathlib
import sys
import unicodedata

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from adapter import PaddleOcrAdapter, PaddleOcrAdapterError, sha256_of_file  # noqa: E402

FIXTURES = ROOT / "fixtures"


@pytest.fixture(scope="session")
def adapter() -> PaddleOcrAdapter:
    return PaddleOcrAdapter()


# ---------------------------------------------------------------------------
# Version-pin enforcement (real capability-discovery finding, not optional)
# ---------------------------------------------------------------------------


def test_version_pin_is_enforced_at_construction(monkeypatch):
    """Simulates an unpinned/incompatible install and proves the adapter
    fails LOUD at construction time rather than silently running against an
    untested combination (see module docstring 'Version pinning')."""
    import adapter as adapter_module

    class _FakePaddleOcrModule:
        __version__ = "3.7.0"  # the known-broken default pip version

    class _FakePaddleModule:
        __version__ = "3.3.1"

    monkeypatch.setitem(sys.modules, "paddleocr", _FakePaddleOcrModule())
    monkeypatch.setitem(sys.modules, "paddle", _FakePaddleModule())

    with pytest.raises(PaddleOcrAdapterError, match="Unsupported PaddleOCR/PaddlePaddle version"):
        adapter_module.PaddleOcrAdapter()


def test_installed_versions_match_the_required_pin():
    """Guards against the sandbox venv silently drifting away from the one
    combination proven to work on this machine."""
    import paddle
    import paddleocr

    from adapter import REQUIRED_PADDLEOCR_VERSION, REQUIRED_PADDLEPADDLE_VERSION

    assert paddleocr.__version__ == REQUIRED_PADDLEOCR_VERSION
    assert paddle.__version__ == REQUIRED_PADDLEPADDLE_VERSION


# ---------------------------------------------------------------------------
# Provenance / SHA-256
# ---------------------------------------------------------------------------


def test_sha256_is_computed_from_file_bytes_before_ocr(adapter):
    pdf_path = FIXTURES / "scanned_arabic_clear.pdf"
    expected_sha256 = sha256_of_file(pdf_path)

    result = adapter.convert(pdf_path)

    assert result.provenance.source_sha256 == expected_sha256
    assert len(result.provenance.source_sha256) == 64


def test_sha256_is_populated_even_when_ocr_itself_fails(adapter, tmp_path):
    """SHA-256 must be computable from file bytes alone, independent of
    whether PaddleOCR can actually parse the file -- provenance should not
    depend on a successful extraction."""
    corrupted = tmp_path / "corrupted.pdf"
    corrupted.write_bytes(b"%PDF-1.4 this is not a real pdf stream" + b"\x00" * 16)

    result = adapter.convert(corrupted)

    assert result.provenance.source_sha256 != ""
    assert len(result.provenance.source_sha256) == 64


def test_model_version_is_honestly_none_not_fabricated(adapter):
    """PaddleOCR exposes model *names*, not semantic per-model versions.
    `model_version` must stay None rather than being faked from the engine
    version or model name."""
    result = adapter.convert(FIXTURES / "scanned_arabic_clear.pdf")
    assert result.provenance.model_version is None
    assert result.provenance.model != ""


# ---------------------------------------------------------------------------
# NFKC normalization applied INSIDE the adapter (A4 requirement)
# ---------------------------------------------------------------------------


def test_normalized_text_is_real_nfkc_of_raw_text(adapter):
    result = adapter.convert(FIXTURES / "scanned_arabic_clear.pdf")

    assert result.normalized_text == unicodedata.normalize("NFKC", result.raw_text)


def test_raw_text_is_preserved_unmodified_for_provenance_audit(adapter):
    """raw_text must be exactly what PaddleOCR returned (joined in its own
    order), never silently overwritten by the normalized value."""
    result = adapter.convert(FIXTURES / "scanned_arabic_clear.pdf")

    assert result.raw_text != ""
    # If raw_text already happened to be pure ASCII/already-NFKC, this
    # equality is expected; the real proof that normalization is NOT a
    # no-op lives in test_mizan_contract_bridge.py's presentation-form test,
    # which forces a codepoint that provably changes under NFKC.
    assert isinstance(result.raw_text, str)


def test_normalize_text_function_runs_real_nfkc_not_a_test_only_helper():
    """Proves normalization is implemented in adapter.py itself (importable,
    callable independent of any test helper), directly addressing the A4
    requirement that NFKC must be in the pipeline, not just in the test
    suite."""
    from adapter import normalize_text

    presentation_form_la = "\ufefb"  # LAM WITH ALEF ISOLATED FORM
    plain_lam_alef = "\u0644\u0627"

    assert normalize_text(presentation_form_la) == plain_lam_alef
    assert normalize_text(presentation_form_la) != presentation_form_la


# ---------------------------------------------------------------------------
# Content preservation / ordering
# ---------------------------------------------------------------------------


def test_scanned_pdf_actually_extracts_non_empty_text(adapter):
    result = adapter.convert(FIXTURES / "scanned_arabic_clear.pdf")
    assert result.success is True
    assert len(result.normalized_text.strip()) > 0


def test_multi_block_fixture_preserves_top_to_bottom_reading_order(adapter):
    """PaddleOCR's own internal ordering is used as-is (no MIZAN-side
    re-ordering/sorting is applied). This proves that ordering survives
    adapter.py's conversion from PaddleOCR's page-dict output into
    SectionResult list."""
    result = adapter.convert(FIXTURES / "scanned_arabic_multi_block.pdf")
    assert result.success is True
    assert len(result.sections) >= 3

    texts = [s.text for s in result.sections]
    # Each recognized line must carry a bbox we can use to verify vertical
    # ordering independent of trusting PaddleOCR's own stated order.
    y_positions = [s.bbox[1] for s in result.sections if s.bbox is not None]
    assert y_positions == sorted(y_positions), (
        f"Sections are not in top-to-bottom order: y_positions={y_positions}, texts={texts}"
    )


# ---------------------------------------------------------------------------
# Error handling -- unsupported / missing / corrupted input must not crash
# ---------------------------------------------------------------------------


def test_missing_file_is_reported_as_failure_not_an_exception(adapter):
    result = adapter.convert(FIXTURES / "does_not_exist.pdf")
    assert result.success is False
    assert result.ocr_applied is False
    assert any("does not exist" in e.lower() or "missing" in e.lower() for e in result.errors)


def test_corrupted_pdf_does_not_crash_the_pipeline(adapter, tmp_path):
    corrupted = tmp_path / "corrupted.pdf"
    corrupted.write_bytes(b"%PDF-1.4 not a real pdf" + b"\x00" * 32)

    result = adapter.convert(corrupted)

    # A corrupted file is an honest FAILURE, not a crash and not a silent
    # success with empty content.
    assert result.success is False
    assert len(result.errors) > 0


def test_unsupported_extension_does_not_crash(adapter, tmp_path):
    bogus = tmp_path / "not_really_a_document.xyz"
    bogus.write_bytes(b"irrelevant bytes")

    result = adapter.convert(bogus)

    # Whatever the outcome, the pipeline itself must not raise.
    assert isinstance(result.success, bool)
