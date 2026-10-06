import dataclasses
import pytest

from mizan_contracts.canonical_v1 import Block, DocumentVersion, Page, RawObservation, Span, normalize_text
from mizan_contracts.identity_v1 import DocumentIdentity, SourceArtifactIdentity
from mizan_contracts.provenance_v1 import ProvenanceRecord, SourceArtifactRecord
from mizan_contracts.stable_locator_v1 import build_document_locator, build_page_locator, build_block_locator, build_span_locator
from mizan_agents.citation_engine import CitationError, create_citation, verify_citation

SHA="a"*64

def fixture():
    dl=build_document_locator(1); pl=build_page_locator(dl,1); bl=build_block_locator(pl,1); sl=build_span_locator(bl,1)
    raw="المبلغ 100 ريال"
    obs=RawObservation(stable_locator=sl,raw_text=raw,normalized_text=normalize_text(raw),produced_by="paddleocr")
    prov=ProvenanceRecord(source_artifact_id="SRC-1",source_sha256=SHA,document_id="DOC-1",document_version_id="DV-1",stable_locator=sl,engine="paddleocr",engine_version="1",settings={},extraction_timestamp="2026-10-06T00:00:00Z",extraction_method="test")
    src=SourceArtifactIdentity(source_artifact_id="SRC-1",sha256=SHA,content_fingerprint="fp",byte_size=10,ingestion_timestamp="2026-10-06T00:00:00Z")
    sr=SourceArtifactRecord(source_artifact_id="SRC-1",sha256=SHA)
    doc=DocumentIdentity(document_id="DOC-1",source_artifact_ids=("SRC-1",),version=1)
    dv=DocumentVersion(document_version_id="DV-1",document_id="DOC-1",version=1)
    page=Page(page_locator=pl,document_version_id="DV-1",page_number=1)
    block=Block(block_locator=bl,page_locator=pl,order_index=0,kind="paragraph")
    span=Span(span_locator=sl,block_locator=bl,start_offset=0,end_offset=len(raw))
    return obs,prov,src,sr,doc,dv,page,block,span

def make():
    o,p,s,sr,d,dv,pg,b,sp=fixture()
    return create_citation(observation_id="OBS-1",observation=o,provenance=p,source_identity=s,source_record=sr,document_identity=d,document_version=dv,page=pg,block=b,span=sp),sr

def test_citation_traces_to_sha_and_exact_hierarchy():
    c,sr=make()
    assert c.source_sha256==SHA
    assert c.span_locator.endswith("SPAN-000001")
    assert verify_citation(c,source_record=sr)

def test_citation_has_no_evidence_or_fact_authority():
    c,_=make()
    assert c.evidentiary_authority is False
    assert c.fact_status is None
    with pytest.raises(CitationError): dataclasses.replace(c,evidentiary_authority=True)
    with pytest.raises(CitationError): dataclasses.replace(c,fact_status="ACCEPTED_FACT")

def test_tampered_sha_fails_verification():
    c,_=make()
    bad=SourceArtifactRecord(source_artifact_id="SRC-1",sha256="b"*64)
    assert not verify_citation(c,source_record=bad)

def test_tampered_citation_id_fails_verification():
    c,sr=make()
    assert not verify_citation(dataclasses.replace(c,citation_id="CIT-forged"),source_record=sr)

def test_observation_provenance_locator_mismatch_rejected():
    o,p,s,sr,d,dv,pg,b,sp=fixture()
    other=dataclasses.replace(o,stable_locator=build_span_locator(b.block_locator,2))
    with pytest.raises(CitationError):
        create_citation(observation_id="OBS-1",observation=other,provenance=p,source_identity=s,source_record=sr,document_identity=d,document_version=dv,page=pg,block=b,span=sp)

def test_wrong_document_version_rejected():
    o,p,s,sr,d,dv,pg,b,sp=fixture()
    bad=DocumentVersion(document_version_id="DV-X",document_id="DOC-1",version=2)
    with pytest.raises(CitationError):
        create_citation(observation_id="OBS-1",observation=o,provenance=p,source_identity=s,source_record=sr,document_identity=d,document_version=bad,page=pg,block=b,span=sp)

def test_wrong_page_hierarchy_rejected():
    o,p,s,sr,d,dv,pg,b,sp=fixture()
    bad=dataclasses.replace(pg,page_locator=build_page_locator(build_document_locator(2),1))
    with pytest.raises(CitationError):
        create_citation(observation_id="OBS-1",observation=o,provenance=p,source_identity=s,source_record=sr,document_identity=d,document_version=dv,page=bad,block=b,span=sp)

def test_offsets_outside_raw_text_rejected():
    o,p,s,sr,d,dv,pg,b,sp=fixture()
    bad=dataclasses.replace(sp,end_offset=len(o.raw_text)+1)
    with pytest.raises(CitationError):
        create_citation(observation_id="OBS-1",observation=o,provenance=p,source_identity=s,source_record=sr,document_identity=d,document_version=dv,page=pg,block=b,span=bad)

def test_citation_id_is_deterministic():
    a,_=make(); b,_=make()
    assert a.citation_id==b.citation_id


def test_normalized_quote_is_derived_from_raw_quote_not_raw_offsets_into_nfkc_text():
    o,p,s,sr,d,dv,pg,b,sp=fixture()
    raw="A\ufb03B"  # NFKC expands the ligature to 'ffi'
    o=RawObservation(stable_locator=sp.span_locator,raw_text=raw,normalized_text=normalize_text(raw),produced_by="paddleocr")
    sp=dataclasses.replace(sp,start_offset=1,end_offset=2)
    c=create_citation(observation_id="OBS-U",observation=o,provenance=p,source_identity=s,source_record=sr,document_identity=d,document_version=dv,page=pg,block=b,span=sp)
    assert c.quoted_raw_text=="\ufb03"
    assert c.quoted_normalized_text=="ffi"
