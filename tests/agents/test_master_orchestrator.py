"""Tests for the MIZAN Agent Society v1 Master Orchestrator."""
import pytest

from mizan_agents.errors import AgentContractError
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


def test_complete_blocked_without_guardian_approval():
    orchestrator = MasterOrchestrator()
    orchestrator.route(_handoff())
    with pytest.raises(AgentContractError):
        orchestrator.complete("T-1")
    assert not orchestrator.is_complete("T-1")


def test_complete_blocked_by_guardian_rejection():
    orchestrator = MasterOrchestrator()
    rejection = Handoff(
        handoff_id="HO-2",
        task_id="T-1",
        from_agent=ARCHITECTURE_GUARDIAN,
        to_agent=CONVERSATION_INTELLIGENCE,
        stage="architecture_review",
        payload={},
        produced_at="t2",
        status="rejected",
        rejection_reason="violates invariant 3",
    )
    orchestrator.route(rejection)
    with pytest.raises(AgentContractError):
        orchestrator.complete("T-1")


def test_complete_succeeds_after_guardian_acceptance():
    orchestrator = MasterOrchestrator()
    acceptance = Handoff(
        handoff_id="HO-3",
        task_id="T-1",
        from_agent=ARCHITECTURE_GUARDIAN,
        to_agent=CONVERSATION_INTELLIGENCE,
        stage="architecture_review",
        payload={},
        produced_at="t3",
        status="accepted",
    )
    orchestrator.route(acceptance)
    assert orchestrator.is_architecture_approved("T-1")
    orchestrator.complete("T-1")
    assert orchestrator.is_complete("T-1")


def test_guardian_approval_for_one_task_does_not_leak_to_another():
    orchestrator = MasterOrchestrator()
    acceptance = Handoff(
        handoff_id="HO-4",
        task_id="T-1",
        from_agent=ARCHITECTURE_GUARDIAN,
        to_agent=CONVERSATION_INTELLIGENCE,
        stage="architecture_review",
        payload={},
        produced_at="t4",
        status="accepted",
    )
    orchestrator.route(acceptance)
    assert orchestrator.is_architecture_approved("T-1")
    assert not orchestrator.is_architecture_approved("T-2")
    with pytest.raises(AgentContractError):
        orchestrator.complete("T-2")
