"""AC-16: Serialization round-trip for each core contract object.

object -> serialize (dataclasses.asdict) -> deserialize (reconstruct) ->
equivalent object, with no loss of identity, provenance, locator, or
raw/normalized text.
"""
import dataclasses

from mizan_contracts import canonical_v1, identity_v1, provenance_v1

_SHA256 = "5" * 64
_SPAN_LOCATOR = "MIZAN-DOC-000001/PAGE-000001/BLOCK-000001/SPAN-000001"


def _round_trip(instance):
    cls = type(instance)
    as_dict = dataclasses.asdict(instance)
    # contract_version is init=False (derived), so it must be dropped before
    # reconstruction, exactly like any other derived/computed field.
    as_dict.pop("contract_version", None)
    rebuilt = cls(**as_dict)
    return rebuilt


def test_raw_observation_round_trips_without_losing_raw_or_normalized_text():
    original = canonical_v1.RawObservation(
        stable_locator=_SPAN_LOCATOR,
        raw_text="\uFEA3",
        normalized_text=canonical_v1.normalize_text("\uFEA3"),
        produced_by="test-engine",
    )
    rebuilt = _round_trip(original)
    assert rebuilt == original
    assert rebuilt.raw_text == original.raw_text
    assert rebuilt.normalized_text == original.normalized_text


def test_source_artifact_identity_round_trips_without_losing_identity_fields():
    original = identity_v1.SourceArtifactIdentity(
        source_artifact_id="A1",
        sha256=_SHA256,
        content_fingerprint="fp1",
        byte_size=123,
        ingestion_timestamp="2026-01-01T00:00:00Z",
    )
    rebuilt = _round_trip(original)
    assert rebuilt == original
    assert rebuilt.sha256 == original.sha256


def test_document_identity_round_trips_preserving_source_artifact_ids():
    original = identity_v1.DocumentIdentity(
        document_id="D1", source_artifact_ids=("A1", "A2"), version=2, parent_version=1
    )
    # tuple survives dataclasses.asdict as a list; reconstruct explicitly.
    as_dict = dataclasses.asdict(original)
    as_dict.pop("contract_version", None)
    as_dict["source_artifact_ids"] = tuple(as_dict["source_artifact_ids"])
    rebuilt = identity_v1.DocumentIdentity(**as_dict)
    assert rebuilt == original
    assert rebuilt.source_artifact_ids == original.source_artifact_ids


def test_provenance_record_round_trips_preserving_locator_and_sha256():
    original = provenance_v1.ProvenanceRecord(
        source_artifact_id="A1",
        source_sha256=_SHA256,
        document_id="D1",
        document_version_id="D1-v1",
        stable_locator=_SPAN_LOCATOR,
        engine="test-engine",
        engine_version="1.0.0",
        settings={"ocr": True},
        extraction_timestamp="2026-01-01T00:00:00Z",
        extraction_method="ocr",
        confidence=0.87,
    )
    rebuilt = _round_trip(original)
    assert rebuilt == original
    assert rebuilt.stable_locator == original.stable_locator
    assert rebuilt.source_sha256 == original.source_sha256
    assert rebuilt.confidence == original.confidence
