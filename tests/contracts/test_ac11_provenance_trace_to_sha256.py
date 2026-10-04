"""AC-11: Provenance trace reaches Source Artifact SHA-256 programmatically,
with no gaps and no engine-state guessing.
"""
import pytest

from mizan_contracts import provenance_v1, stable_locator_v1
from mizan_contracts.errors import ContractValidationError

_SHA256 = "f" * 64


def _build_sample_chain():
    document_locator = stable_locator_v1.build_document_locator(1)
    page_locator = stable_locator_v1.build_page_locator(document_locator, 1)
    block_locator = stable_locator_v1.build_block_locator(page_locator, 1)
    span_locator = stable_locator_v1.build_span_locator(block_locator, 1)

    source_artifact = provenance_v1.SourceArtifactRecord(
        source_artifact_id="A1",
        sha256=_SHA256,
    )
    provenance = provenance_v1.ProvenanceRecord(
        source_artifact_id="A1",
        source_sha256=_SHA256,
        document_id="D1",
        document_version_id="D1-v1",
        stable_locator=span_locator,
        engine="test-engine",
        engine_version="1.0.0",
        settings={},
        extraction_timestamp="2026-01-01T00:00:00Z",
        extraction_method="test-extraction",
    )
    return provenance, source_artifact


def test_observation_traces_to_source_sha256_with_no_gaps():
    provenance, source_artifact = _build_sample_chain()
    resolved_sha256 = provenance_v1.trace_to_source_sha256(provenance, source_artifact)
    assert resolved_sha256 == _SHA256
    # The full path is programmatically walkable from the pieces alone:
    assert provenance.stable_locator.startswith("MIZAN-DOC-000001")
    assert provenance.document_id == "D1"
    assert provenance.source_artifact_id == source_artifact.source_artifact_id
    assert resolved_sha256 == source_artifact.sha256


def test_mismatched_source_artifact_id_breaks_the_chain_loudly():
    provenance, _ = _build_sample_chain()
    wrong_artifact = provenance_v1.SourceArtifactRecord(source_artifact_id="A2", sha256="0" * 64)
    with pytest.raises(ContractValidationError):
        provenance_v1.trace_to_source_sha256(provenance, wrong_artifact)


def test_mismatched_sha256_breaks_the_chain_loudly():
    provenance, _ = _build_sample_chain()
    same_id_wrong_hash = provenance_v1.SourceArtifactRecord(source_artifact_id="A1", sha256="0" * 64)
    with pytest.raises(ContractValidationError):
        provenance_v1.trace_to_source_sha256(provenance, same_id_wrong_hash)
