"""Tests for the MIZAN Agent Society v1 Evolution Agent."""
import pytest

from mizan_agents.errors import AgentContractError
from mizan_agents.evolution_agent import EvolutionAgent, ProposedAmendment
from mizan_agents.memory import GovernedMemory
from mizan_agents.registry import EVOLUTION_AGENT


def test_proposal_is_recorded_in_governed_memory():
    agent = EvolutionAgent()
    memory = GovernedMemory()
    amendment = agent.propose(
        memory,
        proposal_id="P1",
        title="Add Invariant 11",
        rationale="Example rationale for a new invariant.",
        affected_invariants=(9,),
        written_at="2026-01-01T00:00:00Z",
    )
    assert amendment.status == "proposed"
    entry = memory.read(f"{EVOLUTION_AGENT}/proposal/P1")
    assert entry.value["title"] == "Add Invariant 11"
    assert entry.value["status"] == "proposed"


def test_invalid_status_rejected_structurally():
    with pytest.raises(AgentContractError):
        ProposedAmendment(
            proposal_id="P2",
            title="bad",
            rationale="bad",
            affected_invariants=(),
            status="adopted",
        )


def test_invalid_invariant_range_rejected():
    with pytest.raises(AgentContractError):
        ProposedAmendment(
            proposal_id="P3",
            title="bad",
            rationale="bad",
            affected_invariants=(99,),
        )


def test_missing_required_fields_rejected():
    with pytest.raises(AgentContractError):
        ProposedAmendment(proposal_id="", title="", rationale="", affected_invariants=())


def test_duplicate_proposal_id_rejected_by_append_only_memory():
    agent = EvolutionAgent()
    memory = GovernedMemory()
    agent.propose(
        memory,
        proposal_id="P4",
        title="first",
        rationale="first rationale",
        affected_invariants=(1,),
        written_at="t0",
    )
    with pytest.raises(AgentContractError):
        agent.propose(
            memory,
            proposal_id="P4",
            title="second",
            rationale="second rationale",
            affected_invariants=(1,),
            written_at="t1",
        )
