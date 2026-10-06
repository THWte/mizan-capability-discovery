"""Tests for the MIZAN Agent Society v1 Master Orchestrator (v1.1, hardened
approval-binding flow -- see orchestrator.py's module docstring for why the
old "any accepted Handoff from architecture_guardian" check was replaced)."""
import pytest

from mizan_agents.architecture_guardian import ArchitectureGuardianAgent
from mizan_agents.errors import AgentContractError
from mizan_agents.guardian_approval import GuardianApproval
from mizan_agents.handoff_contract import Handoff
from mizan_agents.orchestrator import MasterOrchestrator
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


def test_route_appends_to_history():
    orchestrator = MasterOrchestrator()
    handoff = _handoff()
    orchestrator.route(handoff)
    assert orchestrator.history_for_task("T-1") == (handoff,)


def test_complete_requires_an_approval_argument():
    orchestrator = MasterOrchestrator()
    orchestrator.route(_handoff())
    with pytest.raises(TypeError):
        # complete() now requires an approval argument -- there is no
        # single-argument completion path left to even attempt.
        orchestrator.complete("T-1")
    assert not orchestrator.is_complete("T-1")


def test_complete_blocked_by_guardian_fail_verdict():
    orchestrator = MasterOrchestrator()
    guardian = ArchitectureGuardianAgent()
    handoff = _handoff(payload={"becomes_load_bearing": True})
    orchestrator.route(handoff)
    approval = guardian.approve(handoff, approval_id="GA-1", issued_at="t2")
    assert approval.verdict == "FAIL"
    with pytest.raises(AgentContractError):
        orchestrator.complete("T-1", approval)
    assert not orchestrator.is_complete("T-1")


def test_complete_succeeds_after_real_guardian_approval():
    orchestrator = MasterOrchestrator()
    guardian = ArchitectureGuardianAgent()
    handoff = _handoff()
    orchestrator.route(handoff)
    approval = guardian.approve(handoff, approval_id="GA-2", issued_at="t2")
    assert approval.verdict == "PASS"
    orchestrator.complete("T-1", approval)
    assert orchestrator.is_complete("T-1")


def test_approval_for_one_task_does_not_complete_another():
    orchestrator = MasterOrchestrator()
    guardian = ArchitectureGuardianAgent()
    handoff_t1 = _handoff(handoff_id="HO-T1", task_id="T-1")
    orchestrator.route(handoff_t1)
    approval = guardian.approve(handoff_t1, approval_id="GA-3", issued_at="t2")
    with pytest.raises(AgentContractError):
        orchestrator.complete("T-2", approval)
    assert not orchestrator.is_complete("T-2")


def test_approval_rejected_if_reviewed_handoff_never_routed():
    """A GuardianApproval referencing a handoff_id that was never routed
    through this Orchestrator (e.g. reviewed in isolation, or forged)
    cannot complete anything."""
    orchestrator = MasterOrchestrator()
    guardian = ArchitectureGuardianAgent()
    handoff = _handoff()
    # Deliberately not routed.
    approval = guardian.approve(handoff, approval_id="GA-4", issued_at="t2")
    with pytest.raises(AgentContractError):
        orchestrator.complete("T-1", approval)


def test_approval_rejected_if_payload_mutated_after_review():
    """PART 12: mutating a nested, mutable payload dict after Guardian
    review -- even though the Handoff dataclass itself is frozen -- must be
    caught by the digest re-check at completion time."""
    orchestrator = MasterOrchestrator()
    guardian = ArchitectureGuardianAgent()
    handoff = _handoff(payload={"result": {"value": "safe"}})
    orchestrator.route(handoff)
    approval = guardian.approve(handoff, approval_id="GA-5", issued_at="t2")
    assert approval.verdict == "PASS"
    # Mutate the nested dict in place; the Handoff object itself is frozen,
    # but nothing prevents mutating a mutable value it holds a reference to.
    handoff.payload["result"]["document_id"] = "X"
    handoff.payload["result"]["source_artifact_id"] = "X"
    with pytest.raises(AgentContractError):
        orchestrator.complete("T-1", approval)
    assert not orchestrator.is_complete("T-1")


def test_hand_constructed_approval_without_matching_handoff_is_rejected():
    """A caller who hand-constructs a syntactically valid GuardianApproval
    (bypassing ArchitectureGuardianAgent.approve() entirely) still cannot
    complete a task unless a matching, live Handoff with the same digest
    was actually routed."""
    orchestrator = MasterOrchestrator()
    forged = GuardianApproval(
        approval_id="GA-FORGED",
        task_id="T-1",
        reviewed_handoff_id="HO-NEVER-ROUTED",
        reviewed_payload_digest="a" * 64,
        verdict="PASS",
        coverage="PARTIAL",
        checked_invariants=(3, 4, 5, 10),
        issued_by=ARCHITECTURE_GUARDIAN,
        issued_at="t1",
    )
    with pytest.raises(AgentContractError):
        orchestrator.complete("T-1", forged)
