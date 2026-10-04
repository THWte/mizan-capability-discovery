"""AC-03: raw_text != normalized_text are preserved as independent values
whenever NFKC normalization actually changes the text.
"""
from mizan_contracts import canonical_v1
from mizan_contracts.errors import ContractValidationError
import pytest


def test_nfkc_normalization_changes_arabic_presentation_forms():
    # U+FEA3 (an Arabic presentation-form glyph variant) NFKC-normalizes to
    # the plain Arabic letter U+062D. This mirrors the real defect
    # documented in sandboxes/docling/benchmark/RESULTS.md ("OCR language
    # configuration"): Docling's PDF text extraction can return Arabic in
    # presentation-form codepoints rather than plain letters.
    raw = "\uFEA3"
    normalized = canonical_v1.normalize_text(raw)
    assert normalized != raw, "Test fixture must actually exercise a real NFKC change."
    assert normalized == "\u062D"


def test_raw_and_normalized_text_are_retained_independently_on_section():
    raw = "\uFEA3\uFEA3"
    normalized = canonical_v1.normalize_text(raw)
    section = canonical_v1.Section(
        block_locator="MIZAN-DOC-000001/PAGE-000001/BLOCK-000001",
        level=0,
        raw_text=raw,
        normalized_text=normalized,
    )
    assert section.raw_text == raw
    assert section.normalized_text == normalized
    assert section.raw_text != section.normalized_text


def test_raw_and_normalized_text_are_retained_independently_on_raw_observation():
    raw = "\uFEA3\uFEA3"
    normalized = canonical_v1.normalize_text(raw)
    observation = canonical_v1.RawObservation(
        stable_locator="MIZAN-DOC-000001/PAGE-000001/BLOCK-000001/SPAN-000001",
        raw_text=raw,
        normalized_text=normalized,
        produced_by="test-fixture",
    )
    assert observation.raw_text == raw
    assert observation.normalized_text == normalized
    assert observation.raw_text != observation.normalized_text


def test_normalized_text_cannot_be_an_arbitrary_overwrite_of_raw_text():
    """Adversarial case: a caller must not be able to pass a normalized_text
    that is NOT actually NFKC(raw_text) -- e.g. garbage, a completely
    different string, or raw_text re-used verbatim when NFKC would have
    changed it. This proves normalized_text cannot silently overwrite or
    diverge from raw_text's true normalized form."""
    raw = "\uFEA3"  # NFKC-normalizes to "\u062D", NOT to raw itself.
    with pytest.raises(ContractValidationError):
        canonical_v1.Section(
            block_locator="MIZAN-DOC-000001/PAGE-000001/BLOCK-000001",
            level=0,
            raw_text=raw,
            normalized_text="completely unrelated garbage",
        )
    with pytest.raises(ContractValidationError):
        canonical_v1.RawObservation(
            stable_locator="MIZAN-DOC-000001/PAGE-000001/BLOCK-000001/SPAN-000001",
            raw_text=raw,
            normalized_text=raw,  # unnormalized raw text passed off as normalized
            produced_by="test-fixture",
        )


def test_table_caption_normalization_is_enforced_when_caption_present():
    with pytest.raises(ContractValidationError):
        canonical_v1.Table(
            block_locator="MIZAN-DOC-000001/PAGE-000001/BLOCK-000001",
            cells=(),
            caption_raw_text="\uFEA3",
            caption_normalized_text="\uFEA3",  # should be "\u062D"
        )
    with pytest.raises(ContractValidationError):
        canonical_v1.Table(
            block_locator="MIZAN-DOC-000001/PAGE-000001/BLOCK-000001",
            cells=(),
            caption_raw_text="only raw, no normalized",
        )
