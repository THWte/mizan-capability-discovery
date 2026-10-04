"""AC-06: content_fingerprint does not automatically merge documents.

Two source artifacts with the SAME content_fingerprint but DIFFERENT
source_artifact_id must remain independent, classified only as a duplicate
candidate -- never silently merged, deleted, or collapsed into one
document.
"""
import pytest

from mizan_contracts import identity_v1
from mizan_contracts.errors import ContractValidationError

_SHA_1 = "c" * 64
_SHA_2 = "d" * 64


def _artifact(artifact_id: str, sha256: str, fingerprint: str) -> identity_v1.SourceArtifactIdentity:
    return identity_v1.SourceArtifactIdentity(
        source_artifact_id=artifact_id,
        sha256=sha256,
        content_fingerprint=fingerprint,
        byte_size=100,
        ingestion_timestamp="2026-01-01T00:00:00Z",
    )


def test_same_content_fingerprint_different_artifacts_are_duplicate_candidates_only():
    artifact_1 = _artifact("A1", _SHA_1, "same-fingerprint")
    artifact_2 = _artifact("A2", _SHA_2, "same-fingerprint")

    relationship = identity_v1.classify_duplicate_candidate(artifact_1, artifact_2)

    assert relationship == identity_v1.DuplicateRelationship.DUPLICATE_CANDIDATE
    # Both artifacts remain independently addressable -- no merge occurred.
    assert artifact_1.source_artifact_id != artifact_2.source_artifact_id
    assert artifact_1.sha256 != artifact_2.sha256


def test_different_content_fingerprint_artifacts_are_classified_distinct():
    artifact_1 = _artifact("A1", _SHA_1, "fingerprint-one")
    artifact_2 = _artifact("A2", _SHA_2, "fingerprint-two")

    relationship = identity_v1.classify_duplicate_candidate(artifact_1, artifact_2)

    assert relationship == identity_v1.DuplicateRelationship.CONFIRMED_DISTINCT


def test_classify_duplicate_candidate_never_produces_a_merge_outcome():
    artifact_1 = _artifact("A1", _SHA_1, "same-fingerprint")
    artifact_2 = _artifact("A2", _SHA_2, "same-fingerprint")

    relationship = identity_v1.classify_duplicate_candidate(artifact_1, artifact_2)

    # The contract's vocabulary has no "merged" outcome at all -- only
    # duplicate_candidate / confirmed_same_document / confirmed_distinct,
    # and only an explicit (separate, out-of-scope) MIZAN decision may ever
    # produce CONFIRMED_SAME_DOCUMENT.
    assert relationship != "merged"
    assert relationship == identity_v1.DuplicateRelationship.DUPLICATE_CANDIDATE


def test_comparing_an_artifact_against_itself_is_rejected():
    artifact_1 = _artifact("A1", _SHA_1, "fp")
    with pytest.raises(ContractValidationError):
        identity_v1.classify_duplicate_candidate(artifact_1, artifact_1)
