import pytest

from mizan_contracts.canonical_v1 import RawObservation, normalize_text
from mizan_contracts.identity_v1 import DocumentIdentity, SourceArtifactIdentity
from mizan_contracts.provenance_v1 import ProvenanceRecord, SourceArtifactRecord
from mizan_contracts.stable_locator_v1 import build_document_locator, build_page_locator, build_block_locator, build_span_locator
from mizan_agents.canonical_document_flow import CanonicalFlowError, ObservationEnvelope, run_canonical_document_flow
from mizan_agents.document_routing import DocumentKind, DocumentProfile, PdfMode, Provider
from mizan_agents.evidence_resolution import EvidenceState, resolve_observations

SHA = "a" * 64

def loc(n=1):
    d=build_document_locator(1); p=build_page_locator(d,1); b=build_block_locator(p,1); return build_span_locator(b,n)

def source():
    return SourceArtifactIdentity(source_artifact_id="SRC-1", sha256=SHA, content_fingerprint="fp-1", byte_size=10, ingestion_timestamp="2026-10-06T00:00:00Z")

def document():
    return DocumentIdentity(document_id="DOC-1", source_artifact_ids=("SRC-1",), version=1, source_provenance="test")

def source_record():
    return SourceArtifactRecord(source_artifact_id="SRC-1", sha256=SHA)

def envelope(oid, text, engine, stable=None):
    stable = stable or loc()
    o=RawObservation(stable_locator=stable, raw_text=text, normalized_text=normalize_text(text), produced_by=engine)
    p=ProvenanceRecord(source_artifact_id="SRC-1", source_sha256=SHA, document_id="DOC-1", document_version_id="DOCV-1", stable_locator=stable, engine=engine, engine_version="1", settings={}, extraction_timestamp="2026-10-06T00:00:00Z", extraction_method="test")
    return ObservationEnvelope(observation_id=oid, observation=o, provenance=p)

def scanned():
    return DocumentProfile(kind=DocumentKind.PDF, pdf_mode=PdfMode.SCANNED, arabic_expected=True)

def test_scanned_arabic_flow_routes_paddle_and_preserves_observation_state():
    r=run_canonical_document_flow(source_identity=source(), document_identity=document(), source_record=source_record(), profile=scanned(), observations=[envelope("o1","نص","paddleocr")])
    assert r.route.primary is Provider.PADDLEOCR
    assert r.evidence_resolution.state is EvidenceState.OBSERVED
    assert r.production_approved is False

def test_two_independent_matching_observations_corroborate_only_on_ambiguous_route():
    profile=DocumentProfile(kind=DocumentKind.PDF, pdf_mode=PdfMode.AMBIGUOUS, arabic_expected=True)
    r=run_canonical_document_flow(source_identity=source(), document_identity=document(), source_record=source_record(), profile=profile, observations=[envelope("o1","نص","docling"),envelope("o2","نص","paddleocr")])
    assert r.evidence_resolution.state is EvidenceState.CORROBORATED
    assert r.requires_human_review is True  # route itself is ambiguous

def test_conflict_is_preserved_not_resolved_to_winner():
    profile=DocumentProfile(kind=DocumentKind.PDF, pdf_mode=PdfMode.AMBIGUOUS, arabic_expected=True)
    r=run_canonical_document_flow(source_identity=source(), document_identity=document(), source_record=source_record(), profile=profile, observations=[envelope("o1","100","docling"),envelope("o2","900","paddleocr")])
    assert r.evidence_resolution.state is EvidenceState.CONFLICTED
    assert r.requires_human_review

def test_wrong_engine_for_route_is_rejected():
    with pytest.raises(CanonicalFlowError):
        run_canonical_document_flow(source_identity=source(), document_identity=document(), source_record=source_record(), profile=scanned(), observations=[envelope("o1","نص","docling")])

def test_tampered_source_hash_is_rejected():
    bad=SourceArtifactRecord(source_artifact_id="SRC-1", sha256="b"*64)
    with pytest.raises(CanonicalFlowError):
        run_canonical_document_flow(source_identity=source(), document_identity=document(), source_record=bad, profile=scanned(), observations=[envelope("o1","نص","paddleocr")])

def test_document_source_link_is_required():
    d=DocumentIdentity(document_id="DOC-1", source_artifact_ids=("SRC-X",), version=1)
    with pytest.raises(CanonicalFlowError):
        run_canonical_document_flow(source_identity=source(), document_identity=d, source_record=source_record(), profile=scanned(), observations=[envelope("o1","نص","paddleocr")])

def test_provenance_locator_must_match_observation():
    o=RawObservation(stable_locator=loc(1), raw_text="نص", normalized_text=normalize_text("نص"), produced_by="paddleocr")
    p=ProvenanceRecord(source_artifact_id="SRC-1", source_sha256=SHA, document_id="DOC-1", document_version_id="DOCV-1", stable_locator=loc(2), engine="paddleocr", engine_version="1", settings={}, extraction_timestamp="2026-10-06T00:00:00Z", extraction_method="test")
    with pytest.raises(CanonicalFlowError): ObservationEnvelope(observation_id="o1", observation=o, provenance=p)

def test_same_text_at_different_locators_is_not_corroborated():
    a=envelope("o1","نص","docling",loc(1)); b=envelope("o2","نص","paddleocr",loc(2))
    r=resolve_observations([("o1",a.observation),("o2",b.observation)])
    assert r.state is EvidenceState.REVIEW_REQUIRED
    assert "STABLE_LOCATOR_MISMATCH" in r.reason_codes

def test_no_fact_promotion_surface():
    r=run_canonical_document_flow(source_identity=source(), document_identity=document(), source_record=source_record(), profile=scanned(), observations=[envelope("o1","نص","paddleocr")])
    assert not hasattr(r,"fact") and not hasattr(r,"accepted_fact") and not hasattr(r.evidence_resolution,"verified")

def test_engine_alias_cannot_impersonate_routed_provider():
    with pytest.raises(CanonicalFlowError):
        run_canonical_document_flow(source_identity=source(), document_identity=document(), source_record=source_record(), profile=scanned(), observations=[envelope("o1","نص","PaddleOCR-v3")])

def test_observation_producer_must_match_provenance_engine():
    stable=loc()
    o=RawObservation(stable_locator=stable, raw_text="نص", normalized_text=normalize_text("نص"), produced_by="paddleocr")
    p=ProvenanceRecord(source_artifact_id="SRC-1", source_sha256=SHA, document_id="DOC-1", document_version_id="DOCV-1", stable_locator=stable, engine="docling", engine_version="1", settings={}, extraction_timestamp="2026-10-06T00:00:00Z", extraction_method="test")
    with pytest.raises(CanonicalFlowError):
        ObservationEnvelope(observation_id="o1", observation=o, provenance=p)
