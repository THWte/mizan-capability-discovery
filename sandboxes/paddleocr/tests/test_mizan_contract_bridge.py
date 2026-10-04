"""
MIZAN Contract Bridge - Adversarial & Structural Test Suite (PaddleOCR)

These tests validate `mizan_bridge.py` (the ONLY place PaddleOCR-shaped
output crosses into MIZAN's real core contracts: canonical_v1,
provenance_v1, identity_v1, stable_locator_v1). They build
`NormalizedDocumentResult` instances directly and synthetically -- they do
NOT require PaddleOCR/PaddlePaddle to be installed, because `adapter.py`'s
dataclasses carry no import-time dependency on `paddleocr`/`paddle`
themselves (only `PaddleOcrAdapter.__init__` lazily imports them). This lets
the contract-integration layer be tested fast and deterministically,
independent of whether the OCR/ML stack is installed.

This file intentionally mirrors `sandboxes/docling/tests/test_mizan_contract_bridge.py`
test-for-test where the capability is comparable (same contracts, same
adversarial methodology, per A4's "SAME CER/WER IMPLEMENTATION" /
engine-neutral-methodology instruction) -- it has NO import-time or runtime
dependency on anything in `sandboxes/docling/`.

Run with:

    .venv\\Scripts\\python.exe -m pytest tests/test_mizan_contract_bridge.py -v
"""
from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from adapter import NormalizedDocumentResult, Provenance, SectionResult, TableResult  # noqa: E402
import mizan_bridge  # noqa: E402
from mizan_bridge import BridgeError, bridge_to_mizan, trace_observation_to_sha256  # noqa: E402

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO_ROOT / "contracts"))
from mizan_contracts import identity_v1  # noqa: E402
from mizan_contracts.errors import ContractValidationError  # noqa: E402

# Arabic Presentation Forms-A codepoint for "LAM WITH ALEF ISOLATED FORM"
# (U+FEFB). NFKC normalizes this to the two plain letters LAM + ALEF
# (U+0644 U+0627) -- used here to prove normalization actually ran inside
# the bridge/adapter pipeline, not a pass-through no-op.
PRESENTATION_FORM_LA = "\ufefb"
PLAIN_LAM_ALEF = "\u0644\u0627"


def _make_result(
    *,
    success: bool = True,
    sections: list[SectionResult] | None = None,
    tables: list[TableResult] | None = None,
    sha256: str = "a" * 64,
    size_bytes: int = 1024,
    engine_version: str = "3.3.3",
    raw_text: str = "sample",
    errors: list[str] | None = None,
) -> NormalizedDocumentResult:
    raw_text_full = raw_text
    return NormalizedDocumentResult(
        success=success,
        file_type="pdf",
        raw_text=raw_text_full,
        normalized_text=mizan_bridge.canonical_v1.normalize_text(raw_text_full) if sections is None else raw_text_full,
        sections=sections if sections is not None else [SectionResult(level=0, text=raw_text_full)],
        tables=tables or [],
        metadata={},
        warnings=[],
        errors=errors or [],
        provenance=Provenance(
            source_path="synthetic.pdf",
            source_file_name="synthetic.pdf",
            source_size_bytes=size_bytes,
            source_sha256=sha256,
            engine="paddleocr",
            engine_version=engine_version,
            model="text_det+arabic_rec(lang=ar)",
            model_version=None,
        ),
        processing_time_seconds=0.01,
        ocr_mode="scanned",
        ocr_reason="synthetic fixture",
        ocr_engine="paddleocr(lang=ar)",
        ocr_applied=True,
    )


# ---------------------------------------------------------------------------
# Happy path / structural correctness
# ---------------------------------------------------------------------------


def test_bridge_produces_mizan_owned_locators_not_paddleocr_ids():
    result = _make_result(sections=[SectionResult(level=0, text="Line A"), SectionResult(level=0, text="Line B")])
    output = bridge_to_mizan(result)

    assert output.document_locator.startswith("MIZAN-DOC-")
    for block in output.blocks:
        assert block.block_locator.startswith(output.pages[0].page_locator + "/")
        assert block.kind == "paragraph"  # PaddleOCR has no heading classification capability
    for obs in output.raw_observations:
        assert "paddleocr" not in obs.stable_locator.lower()
        assert "paddle" not in obs.stable_locator.lower()


def test_raw_text_is_preserved_separately_from_normalized_text():
    # Presentation-form Arabic actually changes under NFKC, proving the
    # bridge ran real normalization rather than a pass-through no-op.
    result = _make_result(sections=[SectionResult(level=0, text=PRESENTATION_FORM_LA)])
    output = bridge_to_mizan(result)

    section = output.sections[0]
    assert section.raw_text == PRESENTATION_FORM_LA
    assert section.normalized_text == PLAIN_LAM_ALEF
    assert section.raw_text != section.normalized_text  # proves real work happened, not an overwrite


def test_reverse_traceability_structural_chain_succeeds():
    result = _make_result(sections=[SectionResult(level=0, text="traceable content")])
    output = bridge_to_mizan(result)
    locator = output.raw_observations[0].stable_locator

    sha256 = trace_observation_to_sha256(output, locator)

    assert sha256 == output.source_artifact_identity.sha256 == "a" * 64


def test_two_artifacts_can_point_to_same_document_without_merging():
    result_a = _make_result(sha256="a" * 64, sections=[SectionResult(level=0, text="v1 text")])
    result_b = _make_result(sha256="b" * 64, sections=[SectionResult(level=0, text="v2 text")])

    output_a = bridge_to_mizan(result_a, document_id="doc-shared", document_version=1)
    output_b = bridge_to_mizan(result_b, document_id="doc-shared", document_version=2)

    assert output_a.document.document_id == output_b.document.document_id == "doc-shared"
    assert output_a.document_version.document_version_id != output_b.document_version.document_version_id
    assert output_a.source_artifact_identity.source_artifact_id != output_b.source_artifact_identity.source_artifact_id


def test_same_normalized_content_different_bytes_is_duplicate_candidate_only():
    result_a = _make_result(sha256="a" * 64, sections=[SectionResult(level=0, text="identical content")])
    result_b = _make_result(sha256="b" * 64, sections=[SectionResult(level=0, text="identical content")])

    output_a = bridge_to_mizan(result_a)
    output_b = bridge_to_mizan(result_b)

    assert output_a.source_artifact_identity.content_fingerprint == output_b.source_artifact_identity.content_fingerprint
    assert output_a.source_artifact_identity.sha256 != output_b.source_artifact_identity.sha256

    relationship = identity_v1.classify_duplicate_candidate(
        output_a.source_artifact_identity, output_b.source_artifact_identity
    )
    assert relationship == identity_v1.DuplicateRelationship.DUPLICATE_CANDIDATE
    # Critically: classification never creates or changes a document_id.
    assert output_a.document.document_id != output_b.document.document_id


def test_multi_page_content_is_split_across_distinct_page_entities():
    """Capability difference from the Docling bridge: PaddleOCR reports a
    real per-line page_index, so this bridge creates one MIZAN Page per
    distinct page_number, in first-seen order (see module docstring)."""
    result = _make_result(
        sections=[
            SectionResult(level=0, text="page one line", page_number=1),
            SectionResult(level=0, text="page two line", page_number=2),
            SectionResult(level=0, text="page one again", page_number=1),
        ]
    )
    output = bridge_to_mizan(result)

    assert len(output.pages) == 2
    assert output.pages[0].page_number == 1
    assert output.pages[1].page_number == 2
    # Third section (page 1 again) must reuse the FIRST page's locator, not
    # create a duplicate Page entity.
    block_for_third_section = output.blocks[2]
    assert block_for_third_section.page_locator == output.pages[0].page_locator


# ---------------------------------------------------------------------------
# Adversarial: corrupted / failed extraction
# ---------------------------------------------------------------------------


def test_failed_extraction_is_never_silently_bridged():
    result = _make_result(success=False, errors=["PaddleOcrAdapterError: corrupted file"])
    with pytest.raises(BridgeError):
        bridge_to_mizan(result)


# ---------------------------------------------------------------------------
# Adversarial: SHA-256
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_sha256",
    [
        "",
        "a" * 63,
        "a" * 65,
        "g" * 64,  # non-hex
        "A" * 64,  # uppercase rejected (contract requires lowercase)
    ],
)
def test_missing_or_invalid_sha256_is_rejected(bad_sha256):
    result = _make_result(sha256=bad_sha256)
    with pytest.raises(ContractValidationError):
        bridge_to_mizan(result)


# ---------------------------------------------------------------------------
# Adversarial: raw/normalized text integrity
# ---------------------------------------------------------------------------


def test_normalized_text_overwriting_raw_text_is_rejected():
    from mizan_contracts import canonical_v1

    section = canonical_v1.Section(
        block_locator="MIZAN-DOC-000001/PAGE-000001/BLOCK-000001",
        level=0,
        raw_text="hello",
        normalized_text="hello",
    )
    assert section.normalized_text == "hello"

    with pytest.raises(ContractValidationError):
        canonical_v1.Section(
            block_locator="MIZAN-DOC-000001/PAGE-000001/BLOCK-000001",
            level=0,
            raw_text="hello",
            normalized_text="SOMETHING ELSE ENTIRELY",
        )


# ---------------------------------------------------------------------------
# Adversarial: locator ownership
# ---------------------------------------------------------------------------


def test_engine_native_id_used_as_locator_is_rejected_by_bridge_guard(monkeypatch):
    """Simulate a future bug where the allocator leaks a PaddleOCR-native
    identifier (e.g. a rec_boxes index) into a span locator, and prove the
    bridge's defense-in-depth guard (_emit_observation's explicit
    validate_locator_component call) still catches it."""

    def _poisoned_next_span(self, block_locator):
        return block_locator + "/paddleocr-rec-box-42"

    monkeypatch.setattr(mizan_bridge.LocatorAllocator, "next_span", _poisoned_next_span)

    result = _make_result(sections=[SectionResult(level=0, text="poisoned locator test")])
    with pytest.raises(ContractValidationError):
        bridge_to_mizan(result)


def test_malformed_locator_rejected_at_contract_level():
    from mizan_contracts import stable_locator_v1

    with pytest.raises(ContractValidationError):
        stable_locator_v1.validate_locator_component("paddleocr-internal-ref-99", "span")


# ---------------------------------------------------------------------------
# Adversarial: Observation boundary -- cannot promote to Accepted Fact
# ---------------------------------------------------------------------------


def test_bridge_output_has_no_fact_or_accepted_fact_attribute():
    """Structural proof that BridgeOutput cannot carry a Fact/AcceptedFact:
    no such field exists on the dataclass, and no method on BridgeOutput or
    mizan_bridge promotes a RawObservation into one. This mirrors the
    Docling bridge's equivalent guarantee and enforces the same
    SOURCE -> RAW EXTRACTION -> NORMALIZATION -> INTERPRETATION ->
    VERIFICATION -> ACCEPTED FACT separation for this engine."""
    import dataclasses as _dc

    field_names = {f.name for f in _dc.fields(mizan_bridge.BridgeOutput)}
    assert "fact" not in field_names
    assert "accepted_fact" not in field_names
    assert not hasattr(mizan_bridge, "promote_to_fact")
    assert not hasattr(mizan_bridge, "accept_fact")


def test_engine_confidence_is_not_a_verification_signal():
    """PaddleOCR's own per-line confidence (unlike Docling, which has none)
    must be carried only as an engine-reported value inside provenance
    settings, never exposed as a MIZAN verification/acceptance signal."""
    result = _make_result(sections=[SectionResult(level=0, text="high confidence line", confidence=0.999)])
    output = bridge_to_mizan(result)

    provenance_record = output.provenance_records[0]
    assert provenance_record.settings["engine_confidence"] == pytest.approx(0.999)
    # No VERIFIED/ACCEPTED status field exists anywhere on the record.
    assert not hasattr(provenance_record, "verification_status")
    assert not hasattr(provenance_record, "accepted")
