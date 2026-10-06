"""Tests for the MIZAN Agent Society v1 Architecture Guardian Agent."""
import pytest

from mizan_agents.architecture_guardian import ArchitectureGuardianAgent, GuardianVerdict
from mizan_agents.errors import AgentContractError
from mizan_agents.handoff_contract import Handoff
from mizan_agents.registry import ARCHITECTURE_GUARDIAN, CONVERSATION_INTELLIGENCE


def _handoff(**overrides):
    defaults = dict(
        handoff_id="HO-1",
        task_id="T-1",
        from_agent=CONVERSATION_INTELLIGENCE,
        to_agent=ARCHITECTURE_GUARDIAN,
        stage="architecture_review",
        payload={},
        produced_at="t1",
    )
    defaults.update(overrides)
    return Handoff(**defaults)


def test_clean_payload_passes():
    guardian = ArchitectureGuardianAgent()
    verdict = guardian.review(_handoff(payload={"note": "all good"}))
    assert verdict.verdict == "PASS"
    assert verdict.violated_invariants == ()


def test_docling_id_disguised_as_locator_fails_invariant_3():
    guardian = ArchitectureGuardianAgent()
    verdict = guardian.review(
        _handoff(payload={"stable_locator": "docling-docitem-4f2a"})
    )
    assert verdict.verdict == "FAIL"
    assert 3 in verdict.violated_invariants


def test_mizan_native_locator_passes():
    guardian = ArchitectureGuardianAgent()
    verdict = guardian.review(
        _handoff(payload={"stable_locator": "MIZAN-DOC-000001/PAGE-000001"})
    )
    assert verdict.verdict == "PASS"


def test_load_bearing_engine_fails_invariant_10():
    guardian = ArchitectureGuardianAgent()
    verdict = guardian.review(_handoff(payload={"becomes_load_bearing": True}))
    assert verdict.verdict == "FAIL"
    assert 10 in verdict.violated_invariants


def test_capability_evaluation_without_invariant_9_ref_fails():
    guardian = ArchitectureGuardianAgent()
    verdict = guardian.review(
        _handoff(stage="capability_evaluation", payload={}, invariant_refs=())
    )
    assert verdict.verdict == "FAIL"
    assert 9 in verdict.violated_invariants


def test_capability_evaluation_with_invariant_9_ref_passes():
    guardian = ArchitectureGuardianAgent()
    verdict = guardian.review(
        _handoff(stage="capability_evaluation", payload={}, invariant_refs=(9,))
    )
    assert verdict.verdict == "PASS"


def test_retrieval_score_treated_as_evidence_fails_invariant_4():
    guardian = ArchitectureGuardianAgent()
    verdict = guardian.review(
        _handoff(payload={"retrieval_score": 0.95, "treated_as_evidence": True})
    )
    assert verdict.verdict == "FAIL"
    assert 4 in verdict.violated_invariants


def test_retrieval_score_without_evidence_claim_passes():
    guardian = ArchitectureGuardianAgent()
    verdict = guardian.review(_handoff(payload={"retrieval_score": 0.95}))
    assert verdict.verdict == "PASS"


def test_document_identity_equals_file_identity_fails_invariant_5():
    guardian = ArchitectureGuardianAgent()
    verdict = guardian.review(
        _handoff(payload={"document_id": "X", "source_artifact_id": "X"})
    )
    assert verdict.verdict == "FAIL"
    assert 5 in verdict.violated_invariants


def test_distinct_document_and_artifact_ids_pass():
    guardian = ArchitectureGuardianAgent()
    verdict = guardian.review(
        _handoff(payload={"document_id": "DOC-1", "source_artifact_id": "ART-1"})
    )
    assert verdict.verdict == "PASS"


def test_multiple_violations_all_reported():
    guardian = ArchitectureGuardianAgent()
    verdict = guardian.review(
        _handoff(
            payload={
                "stable_locator": "mineru-block-9",
                "becomes_load_bearing": True,
            }
        )
    )
    assert verdict.verdict == "FAIL"
    assert set(verdict.violated_invariants) == {3, 10}
    assert len(verdict.reasons) == 2


def test_fail_verdict_requires_reasons_structurally():
    with pytest.raises(AgentContractError):
        GuardianVerdict(handoff_id="h", task_id="t", verdict="FAIL")


def test_pass_verdict_cannot_carry_violations_structurally():
    with pytest.raises(AgentContractError):
        GuardianVerdict(
            handoff_id="h", task_id="t", verdict="PASS", violated_invariants=(3,)
        )
