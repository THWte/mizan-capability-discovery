import pytest
from mizan_agents.local_runtime_gate import *
from mizan_agents.golden_review import *
from mizan_agents.engine_hardening import *
from mizan_agents.golden_dataset import *
from mizan_agents.production_readiness import *
from mizan_agents.release_readiness import *

def runtime(status=RuntimeCheckStatus.PASS):
    return LocalRuntimeManifest(
        runtime_id="local-test",os_name="Windows",python_version="3.12",commit_sha="a"*40,
        checks=tuple(RuntimeCheck(name=n,status=status,evidence="verified test evidence" if status is RuntimeCheckStatus.PASS else "") for n in REQUIRED_CHECKS),
    )

def gold():
    c=GoldenCase(case_id="G1",query="q",relevant_citation_ids=("CIT-1",),relevant_span_locators=("MIZAN-DOC-000001/PAGE-000001/BLOCK-000001/SPAN-000001",),label_source="adjudicated",independently_reviewed=True,tier=DatasetTier.ANONYMIZED_VERIFIED)
    return build_manifest(dataset_id="G",version="1",cases=(c,),provenance_note="reviewed")

def ready_decision():
    return assess_production_readiness(ProductionReadinessInput(golden_dataset=gold(),capabilities=(),reverse_traceability_accuracy=1,citation_accuracy=1,critical_test_failures=0,runtime_integration_verified=True))

def test_runtime_requires_every_named_check():
    r=runtime()
    assert verify_local_runtime(r)==(True,())

def test_runtime_missing_check_fails_closed():
    r=runtime()
    r2=dataclasses.replace(r,checks=r.checks[:-1])
    ok,blockers=verify_local_runtime(r2)
    assert not ok and blockers==("MISSING:audit_log",)

def test_runtime_unverified_does_not_pass():
    ok,blockers=verify_local_runtime(runtime(RuntimeCheckStatus.UNVERIFIED))
    assert not ok and len(blockers)==len(REQUIRED_CHECKS)

def test_gold_requires_two_independent_reviewers():
    r=LabelReview(case_id="G1",reviewer_id="R1",verdict=ReviewVerdict.AGREE,citation_ids=("C",),span_locators=("L",),rationale="checked")
    with pytest.raises(GoldenReviewError):
        adjudicate("G1",(r,),adjudicator_id="A",rationale="adjudicated")

def test_gold_disagreement_cannot_be_silently_admitted():
    a=LabelReview(case_id="G1",reviewer_id="R1",verdict=ReviewVerdict.AGREE,citation_ids=("C1",),span_locators=("L1",),rationale="checked")
    b=LabelReview(case_id="G1",reviewer_id="R2",verdict=ReviewVerdict.AGREE,citation_ids=("C2",),span_locators=("L2",),rationale="checked")
    with pytest.raises(GoldenReviewError):
        adjudicate("G1",(a,b),adjudicator_id="A",rationale="cannot silently reconcile")

def test_gold_two_agreeing_reviewers_can_be_adjudicated():
    a=LabelReview(case_id="G1",reviewer_id="R1",verdict=ReviewVerdict.AGREE,citation_ids=("C",),span_locators=("L",),rationale="checked")
    b=LabelReview(case_id="G1",reviewer_id="R2",verdict=ReviewVerdict.AGREE,citation_ids=("C",),span_locators=("L",),rationale="checked")
    out=adjudicate("G1",(a,b),adjudicator_id="A",rationale="agreement verified")
    assert out.independently_reviewed and len(out.reviewer_ids)==2

def test_paddle_concurrency_is_blocked():
    with pytest.raises(RuntimeError):
        assert_execution_allowed("PaddleOCR",concurrency=2,isolated=True)

def test_engines_require_isolation():
    for provider in ("Docling","PaddleOCR"):
        with pytest.raises(RuntimeError):
            assert_execution_allowed(provider,concurrency=1,isolated=False)

def test_sandbox_engines_cannot_be_called_production_approved():
    for provider in ("Docling","PaddleOCR"):
        with pytest.raises(RuntimeError):
            assert_execution_allowed(provider,concurrency=1,isolated=True,production=True)

def test_internal_rc_can_exist_while_production_is_blocked():
    not_ready=assess_production_readiness(ProductionReadinessInput(golden_dataset=gold(),capabilities=(),reverse_traceability_accuracy=.99,citation_accuracy=1,critical_test_failures=0,runtime_integration_verified=True))
    report=build_release_report(commit_sha="a"*40,runtime=runtime(),readiness=not_ready,requested_stage=ReleaseStage.INTERNAL_RC)
    assert report.release_allowed and not report.production_ready

def test_production_rc_requires_production_readiness():
    not_ready=assess_production_readiness(ProductionReadinessInput(golden_dataset=gold(),capabilities=(),reverse_traceability_accuracy=.99,citation_accuracy=1,critical_test_failures=0,runtime_integration_verified=True))
    report=build_release_report(commit_sha="a"*40,runtime=runtime(),readiness=not_ready,requested_stage=ReleaseStage.PRODUCTION_RC)
    assert not report.release_allowed and "PRODUCTION_READINESS_GATE_NOT_READY" in report.blockers

def test_clean_evidence_can_unlock_production_report():
    report=build_release_report(commit_sha="a"*40,runtime=runtime(),readiness=ready_decision(),requested_stage=ReleaseStage.PRODUCTION)
    assert report.release_allowed and report.production_ready and report.runtime_verified
