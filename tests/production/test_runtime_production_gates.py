import pytest
from mizan_agents.golden_dataset import *
from mizan_agents.capability_registry import REGISTRY
from mizan_agents.production_readiness import *
from mizan_agents.intelligence_runtime import RuntimeIntegrationError, RuntimeKnowledgePacket
from mizan_agents.knowledge_layer import KnowledgeClaim,KnowledgeType

def synthetic_manifest():
    c=GoldenCase(case_id="G1",query="ما رقم القضية؟",relevant_citation_ids=("CIT-1",),relevant_span_locators=("MIZAN-DOC-000001/PAGE-000001/BLOCK-000001/SPAN-000001",),label_source="synthetic-fixture",independently_reviewed=True,tier=DatasetTier.SYNTHETIC)
    return build_manifest(dataset_id="SYN",version="1",cases=(c,),provenance_note="No real case data")

def reviewed_manifest():
    c=GoldenCase(case_id="G1",query="سؤال قانوني مجهول الهوية",relevant_citation_ids=("CIT-1",),relevant_span_locators=("MIZAN-DOC-000001/PAGE-000001/BLOCK-000001/SPAN-000001",),label_source="two-reviewer-adjudication",independently_reviewed=True,tier=DatasetTier.ANONYMIZED_VERIFIED)
    return build_manifest(dataset_id="GOLD",version="1",cases=(c,),provenance_note="anonymized and independently reviewed")

def test_synthetic_dataset_can_never_unlock_production():
    inp=ProductionReadinessInput(golden_dataset=synthetic_manifest(),capabilities=(),reverse_traceability_accuracy=1,citation_accuracy=1,critical_test_failures=0,runtime_integration_verified=True)
    out=assess_production_readiness(inp)
    assert out.status==ReadinessStatus.NOT_READY
    assert "NON_SYNTHETIC_INDEPENDENTLY_REVIEWED_GOLDEN_DATASET_REQUIRED" in out.blockers

def test_current_registry_blocks_production_for_known_engine_risks():
    inp=ProductionReadinessInput(golden_dataset=reviewed_manifest(),capabilities=REGISTRY,reverse_traceability_accuracy=1,citation_accuracy=1,critical_test_failures=0,runtime_integration_verified=True)
    out=assess_production_readiness(inp)
    assert out.status==ReadinessStatus.NOT_READY
    assert any("Docling:WINDOWS_STABILITY_UNRESOLVED"==x for x in out.blockers)
    assert any("PaddleOCR:CONCURRENT_CONVERT_UNSAFE"==x for x in out.blockers)

def test_trace_and_citation_are_hard_100_percent_gates():
    inp=ProductionReadinessInput(golden_dataset=reviewed_manifest(),capabilities=(),reverse_traceability_accuracy=.999,citation_accuracy=.999,critical_test_failures=0,runtime_integration_verified=True)
    out=assess_production_readiness(inp)
    assert "REVERSE_TRACEABILITY_MUST_BE_100_PERCENT" in out.blockers
    assert "CITATION_ACCURACY_MUST_BE_100_PERCENT" in out.blockers

def test_runtime_integration_is_mandatory():
    inp=ProductionReadinessInput(golden_dataset=reviewed_manifest(),capabilities=(),reverse_traceability_accuracy=1,citation_accuracy=1,critical_test_failures=0,runtime_integration_verified=False)
    assert "RUNTIME_INTEGRATION_NOT_VERIFIED" in assess_production_readiness(inp).blockers

def test_non_synthetic_gold_requires_independent_review():
    with pytest.raises(GoldenDatasetError):
        GoldenCase(case_id="x",query="q",relevant_citation_ids=("c",),relevant_span_locators=("l",),label_source="source",independently_reviewed=False,tier=DatasetTier.ANONYMIZED_VERIFIED)

def test_manifest_hash_is_deterministic():
    a=reviewed_manifest(); b=reviewed_manifest()
    assert a.sha256==b.sha256 and len(a.sha256)==64

def test_current_capability_registry_is_honest():
    by_provider={x.provider:x for x in REGISTRY}
    assert by_provider["Docling"].production_approved is False
    assert by_provider["PaddleOCR"].production_approved is False
    assert by_provider["pgvector"].production_approved is False
    assert by_provider["BAAI/bge-m3"].production_approved is False

def test_no_current_registry_record_claims_production():
    assert not any(x.production_approved for x in REGISTRY)
