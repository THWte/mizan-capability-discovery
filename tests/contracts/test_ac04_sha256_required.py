"""AC-04: SHA-256 is mandatory for a Source Artifact, and must be a valid
64-hex-character digest.
"""
import pytest

from mizan_contracts import identity_v1
from mizan_contracts.errors import ContractValidationError

_VALID_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def test_source_artifact_without_sha256_is_rejected():
    with pytest.raises(TypeError):
        identity_v1.SourceArtifactIdentity(  # type: ignore[call-arg]
            source_artifact_id="A1",
            content_fingerprint="fp1",
            byte_size=10,
            ingestion_timestamp="2026-01-01T00:00:00Z",
        )


def test_source_artifact_with_invalid_sha256_is_rejected():
    with pytest.raises(ContractValidationError):
        identity_v1.SourceArtifactIdentity(
            source_artifact_id="A1",
            sha256="not-a-valid-sha256",
            content_fingerprint="fp1",
            byte_size=10,
            ingestion_timestamp="2026-01-01T00:00:00Z",
        )


def test_source_artifact_with_valid_sha256_is_accepted():
    artifact = identity_v1.SourceArtifactIdentity(
        source_artifact_id="A1",
        sha256=_VALID_SHA256,
        content_fingerprint="fp1",
        byte_size=10,
        ingestion_timestamp="2026-01-01T00:00:00Z",
    )
    assert artifact.sha256 == _VALID_SHA256
    assert len(artifact.sha256) == 64


@pytest.mark.parametrize(
    "bad_value",
    [
        "",
        "abc123",
        _VALID_SHA256.upper(),  # must be lowercase
        _VALID_SHA256[:-1],  # 63 chars
        _VALID_SHA256 + "0",  # 65 chars
        _VALID_SHA256[:-1] + "g",  # non-hex character
        None,
    ],
)
def test_validate_sha256_rejects_every_invalid_form(bad_value):
    with pytest.raises(ContractValidationError):
        identity_v1.validate_sha256(bad_value)
