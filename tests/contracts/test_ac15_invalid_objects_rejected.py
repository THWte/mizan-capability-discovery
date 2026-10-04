"""AC-15: Invalid objects are rejected deterministically across all four
contracts.
"""
import pytest

from mizan_contracts import canonical_v1, identity_v1, provenance_v1, stable_locator_v1
from mizan_contracts.errors import ContractValidationError

_VALID_SHA256 = "4" * 64
_SPAN_LOCATOR = "MIZAN-DOC-000001/PAGE-000001/BLOCK-000001/SPAN-000001"


def test_missing_sha256_rejected():
    with pytest.raises(TypeError):
        identity_v1.SourceArtifactIdentity(  # type: ignore[call-arg]
            source_artifact_id="A1", content_fingerprint="fp", byte_size=1, ingestion_timestamp="t"
        )


def test_invalid_sha256_rejected():
    with pytest.raises(ContractValidationError):
        identity_v1.SourceArtifactIdentity(
            source_artifact_id="A1",
            sha256="xyz",
            content_fingerprint="fp",
            byte_size=1,
            ingestion_timestamp="t",
        )


def test_missing_document_id_rejected():
    with pytest.raises(TypeError):
        canonical_v1.Document()  # type: ignore[call-arg]
    with pytest.raises(ContractValidationError):
        canonical_v1.Document(document_id="")


def test_missing_source_artifact_id_rejected():
    with pytest.raises(TypeError):
        canonical_v1.SourceArtifact()  # type: ignore[call-arg]
    with pytest.raises(ContractValidationError):
        canonical_v1.SourceArtifact(source_artifact_id="")


def test_invalid_locator_rejected():
    with pytest.raises(ContractValidationError):
        stable_locator_v1.validate_locator_component("not-a-locator", "document")
    with pytest.raises(ContractValidationError):
        stable_locator_v1.validate_locator_component("", "document")


def test_broken_locator_hierarchy_rejected():
    document_locator = stable_locator_v1.build_document_locator(1)
    other_document_locator = stable_locator_v1.build_document_locator(2)
    page_locator = stable_locator_v1.build_page_locator(other_document_locator, 1)
    with pytest.raises(ContractValidationError):
        stable_locator_v1.validate_hierarchy_consistency(document_locator, page_locator)


def test_missing_required_provenance_rejected():
    with pytest.raises(TypeError):
        provenance_v1.ProvenanceRecord()  # type: ignore[call-arg]
    with pytest.raises(ContractValidationError):
        provenance_v1.ProvenanceRecord(
            source_artifact_id="",
            source_sha256=_VALID_SHA256,
            document_id="D1",
            document_version_id="D1-v1",
            stable_locator=_SPAN_LOCATOR,
            engine="e",
            engine_version="1",
            settings={},
            extraction_timestamp="t",
            extraction_method="m",
        )
