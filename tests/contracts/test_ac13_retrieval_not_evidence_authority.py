"""AC-13: Retrieval metadata (score/similarity/rank) cannot modify Evidence
or Verification state through this contract's API.
"""
import pytest

from mizan_contracts import provenance_v1, canonical_v1

_SHA256 = "2" * 64
_SPAN_LOCATOR = "MIZAN-DOC-000001/PAGE-000001/BLOCK-000001/SPAN-000001"


def _base_provenance_kwargs():
    return dict(
        source_artifact_id="A1",
        source_sha256=_SHA256,
        document_id="D1",
        document_version_id="D1-v1",
        stable_locator=_SPAN_LOCATOR,
        engine="test-engine",
        engine_version="1.0.0",
        settings={},
        extraction_timestamp="2026-01-01T00:00:00Z",
        extraction_method="test-extraction",
    )


def test_retrieval_score_cannot_be_passed_into_provenance_record():
    with pytest.raises(TypeError):
        provenance_v1.ProvenanceRecord(
            **_base_provenance_kwargs(),
            retrieval_score=1.0,  # type: ignore[call-arg]
        )


def test_similarity_and_rank_cannot_be_passed_into_provenance_record():
    with pytest.raises(TypeError):
        provenance_v1.ProvenanceRecord(
            **_base_provenance_kwargs(),
            similarity=1.0,  # type: ignore[call-arg]
            rank=1,  # type: ignore[call-arg]
        )


def test_retrieval_score_cannot_be_passed_into_raw_observation():
    with pytest.raises(TypeError):
        canonical_v1.RawObservation(
            stable_locator=_SPAN_LOCATOR,
            raw_text="x",
            normalized_text="x",
            produced_by="test",
            retrieval_score=1.0,  # type: ignore[call-arg]
        )


def test_neither_contract_exposes_a_retrieval_or_rank_field():
    import dataclasses

    for cls in (provenance_v1.ProvenanceRecord, canonical_v1.RawObservation):
        field_names = {f.name.lower() for f in dataclasses.fields(cls)}
        assert not any("retrieval" in name or "similarity" in name or name == "rank" for name in field_names), (
            f"{cls.__name__} must not expose any retrieval/ranking field."
        )
