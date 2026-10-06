import pytest
from mizan_agents.epistemic import validate_no_promoted_epistemic_state
from mizan_agents.errors import AgentContractError
from mizan_agents.evidence_resolution import *
from mizan_agents.knowledge_layer import *
from mizan_agents.verification_gate import *
from mizan_agents.legal_reasoning import *
from mizan_contracts.canonical_v1 import RawObservation

def obs(text,producer="engine-a",loc="MIZAN-DOC-000001/PAGE-000001/BLOCK-000001/SPAN-000001"):
    return RawObservation(raw_text=text,normalized_text=text,produced_by=producer,stable_locator=loc)

def resolution(text="ثبت السداد"):
    return resolve_observations([("O1",obs(text,"a")),("O2",obs(text,"b"))])

def test_promoted_state_value_is_blocked_recursively():
    with pytest.raises(AgentContractError):
        validate_no_promoted_epistemic_state({"nested":[{"epistemic_state":"ACCEPTED_FACT"}]})

def test_candidate_fact_requires_verification_and_is_not_accepted():
    r=resolution()
    k=propose_claim(kind=KnowledgeType.CANDIDATE_FACT,statement="ثبت السداد",case_id="CASE-1",resolution=r,citation_ids=("CIT-1",),confidence=.9)
    assert k.requires_verification and not k.accepted

def test_rejected_evidence_cannot_seed_knowledge():
    o=obs("x")
    r=reject("O1",o,reason_code="INVALID")
    with pytest.raises(KnowledgeError): propose_claim(kind=KnowledgeType.ENTITY,statement="x",case_id="C",resolution=r)

def test_conflict_stays_review_required():
    r=resolve_observations([("O1",obs("تم السداد","a")),("O2",obs("لم يتم السداد","b"))])
    k=propose_claim(kind=KnowledgeType.TEMPORAL_CLAIM,statement="حالة السداد",case_id="C",resolution=r)
    assert r.state==EvidenceState.CONFLICTED and k.requires_verification

def test_verification_requires_citation():
    k=propose_claim(kind=KnowledgeType.CANDIDATE_FACT,statement="x",case_id="C",resolution=resolution("x"))
    with pytest.raises(VerificationError): verify_candidate(k,verifier="human",rationale="checked",source_citations=(),approve=True)

def test_verification_does_not_create_accepted_fact():
    k=propose_claim(kind=KnowledgeType.CANDIDATE_FACT,statement="x",case_id="C",resolution=resolution("x"))
    v=verify_candidate(k,verifier="human",rationale="checked",source_citations=("CIT-1",),approve=True)
    assert v.outcome=="VERIFIED" and v.accepted_fact_id is None

def test_reasoning_preserves_both_sides_and_uncertainty():
    r=resolution()
    a=propose_claim(kind=KnowledgeType.CANDIDATE_FACT,statement="العقد نافذ",case_id="C",resolution=r)
    b=propose_claim(kind=KnowledgeType.CANDIDATE_FACT,statement="يوجد دفع بالفسخ",case_id="C",resolution=r)
    issue=LegalIssue(issue_id="I1",case_id="C",question="هل العقد نافذ؟",supporting_claim_ids=(a.knowledge_id,),opposing_claim_ids=(b.knowledge_id,))
    out=analyze_issue(issue,(a,b),proposition="النفاذ محل نزاع")
    assert out.uncertainty=="MEDIUM" and out.requires_human_review and not out.authoritative

def test_cross_case_reasoning_fails_closed():
    r=resolution()
    a=propose_claim(kind=KnowledgeType.ENTITY,statement="x",case_id="A",resolution=r)
    issue=LegalIssue(issue_id="I",case_id="B",question="q",supporting_claim_ids=(a.knowledge_id,))
    with pytest.raises(ReasoningError): analyze_issue(issue,(a,),proposition="p")

def test_reasoning_cannot_predict_outcome():
    with pytest.raises(ReasoningError): ReasoningConclusion(reasoning_id="R",case_id="C",issue_id="I",proposition="p",support_ids=("K",),counter_ids=(),uncertainty="LOW",outcome_prediction=True)
