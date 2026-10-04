"""AC-05: Document Identity is separate from File (Source Artifact) Identity.

A logical document D1 can be represented by two different source artifacts
A1/A2 (e.g. a scanned PDF and a re-typed DOCX of the same contract) without
document_id ever being forced to equal either source_artifact_id.
"""
import pytest

from mizan_contracts import identity_v1
from mizan_contracts.errors import ContractValidationError

_SHA_A1 = "a" * 64
_SHA_A2 = "b" * 64


def test_document_identity_is_never_equal_to_a_source_artifact_id():
    artifact_a1 = identity_v1.SourceArtifactIdentity(
        source_artifact_id="A1",
        sha256=_SHA_A1,
        content_fingerprint="fp-scan",
        byte_size=1000,
        ingestion_timestamp="2026-01-01T00:00:00Z",
    )
    artifact_a2 = identity_v1.SourceArtifactIdentity(
        source_artifact_id="A2",
        sha256=_SHA_A2,
        content_fingerprint="fp-retyped",
        byte_size=800,
        ingestion_timestamp="2026-01-02T00:00:00Z",
    )

    document = identity_v1.DocumentIdentity(
        document_id="D1",
        source_artifact_ids=(artifact_a1.source_artifact_id, artifact_a2.source_artifact_id),
        version=1,
    )

    assert document.document_id == "D1"
    assert document.document_id not in document.source_artifact_ids
    assert artifact_a1.source_artifact_id != document.document_id
    assert artifact_a2.source_artifact_id != document.document_id
    # Both artifacts legitimately belong to the same logical document.
    assert set(document.source_artifact_ids) == {"A1", "A2"}


def test_document_id_equal_to_a_source_artifact_id_is_rejected():
    with pytest.raises(ContractValidationError):
        identity_v1.DocumentIdentity(
            document_id="A1",  # same value as a source_artifact_id -- forbidden
            source_artifact_ids=("A1",),
            version=1,
        )


def test_document_identity_requires_at_least_one_source_artifact():
    with pytest.raises(ContractValidationError):
        identity_v1.DocumentIdentity(document_id="D1", source_artifact_ids=(), version=1)
