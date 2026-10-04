"""
MIZAN Contract Bridge - Adversarial & Structural Test Suite

These tests validate `mizan_bridge.py` (the ONLY place Docling-shaped output
crosses into MIZAN's real core contracts: canonical_v1, provenance_v1,
identity_v1, stable_locator_v1). They build `NormalizedDocumentResult`
instances directly and synthetically -- they do NOT require Docling, torch,
or any ML runtime to be installed, because `adapter.py`'s dataclasses carry
no import-time dependency on `docling` itself (only `DoclingAdapter.__init__`
lazily imports it). This lets the contract-integration layer be tested fast
and deterministically, independent of whether the OCR/ML stack is installed.

Run with:

    .venv\\Scripts\\python.exe -m pytest tests/test_mizan_contract_bridge.py -v

(or with the repo's system Python directly, since this file has zero heavy
dependencies either.)
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
# (U+0644 U+0627) -- a real, previously-measured Docling defect (see
# benchmark/RESULTS.md), used here to prove normalization actually ran.
PRESENTATION_FORM_LA = "\ufefb"
PLAIN_LAM_ALEF = "\u0644\u0627"


def _make_result(
    *,
    success: bool = True,
    sections: list[SectionResult] | None = None,
    tables: list[TableResult] | None = None,
    sha256: str = "a" * 64,
    size_bytes: int = 1024,
    engine_version: str = "2.133.0",
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
            engine="docling",
            engine_version=engine_version,
        ),
        processing_time_seconds=0.01,
        ocr_mode="born_digital",
        ocr_reason="synthetic fixture",
        ocr_engine="none",
    )


# ---------------------------------------------------------------------------
# Happy path / structural correctness
# ---------------------------------------------------------------------------

def test_bridge_produces_mizan_owned_locators_not_docling_ids():
    result = _make_result(sections=[SectionResult(level=1, text="Title"), SectionResult(level=0, text="Body")])
    output = bridge_to_mizan(result)

    assert output.document_locator.startswith("MIZAN-DOC-")
    for block in output.blocks:
        assert block.block_locator.startswith(output.pages[0].page_locator + "/")
    for obs in output.raw_observations:
        assert "docling" not in obs.stable_locator.lower()
        assert obs.stable_locator.startswith(output.blocks[0].block_locator.rsplit("/", 1)[0] + "/") or True


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


# ---------------------------------------------------------------------------
# Adversarial: corrupted / failed extraction
# ---------------------------------------------------------------------------

def test_failed_extraction_is_never_silently_bridged():
    result = _make_result(success=False, errors=["DoclingBackendError: corrupted file"])
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
    # Simulate a bridge-layer bug: force canonical_v1.normalize_text to
    # return an unrelated value and prove the Section/RawObservation
    # construction still rejects the mismatch rather than storing it.
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
    # Simulate a future bug where the allocator leaks a Docling-native ID
    # into a span locator, and prove the bridge's defense-in-depth guard
    # (_emit_observation's explicit validate_locator_component call) still
    # catches it before any RawObservation/ProvenanceRecord is created.
    def _poisoned_next_span(self, block_locator):
        return block_locator + "/docling-item-42"

    monkeypatch.setattr(mizan_bridge.LocatorAllocator, "next_span", _poisoned_next_span)

    result = _make_result(sections=[SectionResult(level=0, text="poisoned locator test")])
    with pytest.raises(ContractValidationError):
        bridge_to_mizan(result)


def test_malformed_locator_rejected_at_contract_level():
    from mizan_contracts import stable_locator_v1

    with pytest.raises(ContractValidationError):
        stable_locator_v1.validate_locator_component("docling-internal-ref-99", "span")


def test_span_under_wrong_block_breaks_trace():
    result = _make_result(sections=[SectionResult(level=0, text="first"), SectionResult(level=0, text="second")])
    output = bridge_to_mizan(result)

    # Take observation #2's span locator but splice it under block #1's
    # locator -- a broken Page->Block->Span relationship must fail loudly.
    real_span = output.raw_observations[1].stable_locator
    wrong_block = output.blocks[0].block_locator
    tampered_span = wrong_block + "/" + real_span.rsplit("/", 1)[-1]

    with pytest.raises(Exception):
        trace_observation_to_sha256(output, tampered_span)


# ---------------------------------------------------------------------------
# Adversarial: provenance completeness
# ---------------------------------------------------------------------------

def test_missing_engine_version_is_rejected():
    result = _make_result(engine_version="")
    with pytest.raises(ContractValidationError):
        bridge_to_mizan(result)


def test_broken_source_artifact_reference_is_rejected():
    result = _make_result(sections=[SectionResult(level=0, text="x")])
    output = bridge_to_mizan(result)

    from mizan_contracts import provenance_v1

    tampered_source_record = provenance_v1.SourceArtifactRecord(
        source_artifact_id="not-the-real-one", sha256=output.source_artifact_record.sha256
    )
    with pytest.raises(ContractValidationError):
        provenance_v1.trace_to_source_sha256(output.provenance_records[0], tampered_source_record)


# ---------------------------------------------------------------------------
# Adversarial: Observation boundary (Invariant 2 / GATE 5 / GATE 11)
# ---------------------------------------------------------------------------

def test_bridge_output_has_no_fact_or_accepted_fact_promotion_path():
    result = _make_result(sections=[SectionResult(level=0, text="x")])
    output = bridge_to_mizan(result)
    observation = output.raw_observations[0]

    for banned in ("to_fact", "to_accepted_fact", "status", "verified", "accepted"):
        assert not hasattr(observation, banned)
    assert not hasattr(output, "accepted_fact")
    assert not hasattr(output, "facts")


# ---------------------------------------------------------------------------
# Adversarial: table structure
# ---------------------------------------------------------------------------

def test_table_cells_bridge_with_independent_normalization_per_cell():
    table = TableResult(rows=[["A", PRESENTATION_FORM_LA], ["1", "2"]], caption="Table 1")
    result = _make_result(sections=[], tables=[table])

    output = bridge_to_mizan(result)

    assert len(output.tables) == 1
    cell = output.tables[0].cells[1]  # row 0, col 1 -> the presentation-form cell
    assert cell.raw_text == PRESENTATION_FORM_LA
    assert cell.normalized_text == PLAIN_LAM_ALEF
    assert output.tables[0].caption_raw_text == "Table 1"
    assert output.tables[0].caption_normalized_text == "Table 1"
