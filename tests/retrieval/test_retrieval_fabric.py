import pytest
from mizan_agents.retrieval_fabric import *

def C(i,text,doc="D",case="C1"):
    return RetrievalCandidate(candidate_id=i,text=text,span_locator=f"MIZAN-DOC-000001/PAGE-000001/BLOCK-000001/SPAN-{int(i[1:]):06d}",citation_id=f"CIT-{i}",source_artifact_id="SRC-1",document_id=doc,metadata={"case_id":case})

def test_exact_case_number_overrides_dense_near_match():
    cs=[C("C1","القضية رقم 4870236421 تتعلق بنزاع مهني"),C("C2","القضية رقم 4870236422 تتعلق بنزاع مهني")]
    assert RetrievalFabric(dense_scorer=lambda q,c:[0.1,0.99]).search(RetrievalQuery(text="القضية 4870236421",top_k=1),cs).candidates[0].candidate_id=="C1"

def test_amount_precision_overrides_semantic_similarity():
    cs=[C("C1","المطالبة بمبلغ 500000 ريال تعويضاً"),C("C2","المطالبة بمبلغ 50000 ريال تعويضاً")]
    assert RetrievalFabric(dense_scorer=lambda q,c:[0.2,0.99]).search(RetrievalQuery(text="تعويض 500000 ريال",top_k=1),cs).candidates[0].candidate_id=="C1"

def test_appeal_reversal_beats_affirmance():
    cs=[C("C1","ألغت محكمة الاستئناف الحكم الابتدائي وقضت مجدداً"),C("C2","أيدت محكمة الاستئناف الحكم الابتدائي وأبقت النتيجة")]
    assert RetrievalFabric(dense_scorer=lambda q,c:[0.4,0.95]).search(RetrievalQuery(text="الاستئناف ألغى الحكم الأول",top_k=1),cs).candidates[0].candidate_id=="C1"

def test_case_scope_prevents_cross_case_leak():
    cs=[C("C1","ذات العبارة",case="A"),C("C2","ذات العبارة",case="B")]
    r=RetrievalFabric().search(RetrievalQuery(text="ذات العبارة",case_scope=("A",)),cs)
    assert [x.metadata["case_id"] for x in r.candidates]==["A"]

def test_retrieval_cannot_claim_authority_or_fact():
    with pytest.raises(RetrievalError): RetrievalCandidate(candidate_id="x",text="x",span_locator="L",citation_id="C",source_artifact_id="S",document_id="D",retrieval_authority=True)
    with pytest.raises(RetrievalError): RetrievalCandidate(candidate_id="x",text="x",span_locator="L",citation_id="C",source_artifact_id="S",document_id="D",fact_status="ACCEPTED_FACT")
    with pytest.raises(RetrievalError): RetrievalResult(query="q",candidates=(),authoritative=True)

def test_requires_mizan_locator_and_citation_presence():
    with pytest.raises(RetrievalError): RetrievalCandidate(candidate_id="x",text="x",span_locator="",citation_id="C",source_artifact_id="S",document_id="D")

def test_dense_scorer_mismatch_fails_closed():
    with pytest.raises(RetrievalError): RetrievalFabric(dense_scorer=lambda q,c:[]).search(RetrievalQuery(text="x"),[C("C1","x")])

def test_arabic_digit_normalization():
    assert normalize_arabic("القضية ٤٨٧٠٢٣٦٤٢١") == normalize_arabic("القضية 4870236421")
