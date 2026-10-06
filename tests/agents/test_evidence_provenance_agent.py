"""Tests for the MIZAN Agent Society v1 Evidence/Provenance Agent."""
import pytest
from mizan_contracts.provenance_v1 import ProvenanceRecord, SourceArtifactRecord

from mizan_agents.errors import AgentContractError
from mizan_agents.evidence_provenance import EvidenceProvenanceAgent


def _provenance(**overrides):
    defaults = dict(
        source_artifact_id="ART-1",
        source_sha256="a" * 64,
        document_id="DOC-1",
        document_version_id="DOCV-1",
        stable_locator="MIZAN-DOC-000001/PAGE-000001/BLOCK-000001/SPAN-000001",
        engine="example-engine",
        engine_version="1.0.0",
        settings={},
        extraction_timestamp="2026-01-01T00:00:00Z",
        extraction_method="ocr",
    )
    defaults.update(overrides)
    return ProvenanceRecord(**defaults)


def test_resolve_succeeds_for_matching_chain():
    agent = EvidenceProvenanceAgent()
    provenance = _provenance()
    source = SourceArtifactRecord(source_artifact_id="ART-1", sha256="a" * 64)
    evidence = agent.resolve(provenance, source)
    assert evidence.source_sha256 == "a" * 64
    assert evidence.engine == "example-engine"
    assert evidence.stable_locator == provenance.stable_locator


def test_resolve_rejects_mismatched_source_artifact_id():
    agent = EvidenceProvenanceAgent()
    provenance = _provenance(source_artifact_id="ART-1")
    source = SourceArtifactRecord(source_artifact_id="ART-2", sha256="a" * 64)
    with pytest.raises(AgentContractError):
        agent.resolve(provenance, source)


def test_resolve_rejects_mismatched_sha256():
    agent = EvidenceProvenanceAgent()
    provenance = _provenance(source_sha256="a" * 64)
    source = SourceArtifactRecord(source_artifact_id="ART-1", sha256="b" * 64)
    with pytest.raises(AgentContractError):
        agent.resolve(provenance, source)


def test_evidence_record_has_no_promotion_path():
    """EvidenceRecord must have exactly the Evidence-stage fields -- no
    status, no to_fact(), no to_accepted_fact()."""
    agent = EvidenceProvenanceAgent()
    provenance = _provenance()
    source = SourceArtifactRecord(source_artifact_id="ART-1", sha256="a" * 64)
    evidence = agent.resolve(provenance, source)
    assert not hasattr(evidence, "to_fact")
    assert not hasattr(evidence, "to_accepted_fact")
    assert not hasattr(evidence, "status")
    import dataclasses

    field_names = {f.name for f in dataclasses.fields(evidence)}
    assert field_names == {"stable_locator", "source_sha256", "engine"}
