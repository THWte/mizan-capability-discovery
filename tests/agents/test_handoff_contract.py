"""Tests for the MIZAN Agent Society v1 Handoff Contract."""
import pytest

from mizan_agents.errors import AgentContractError
from mizan_agents.handoff_contract import Handoff
from mizan_agents.registry import (
    ARCHITECTURE_GUARDIAN,
    CONVERSATION_INTELLIGENCE,
    MASTER_ORCHESTRATOR,
)


def _make(**overrides):
    defaults = dict(
        handoff_id="HO-000001",
        task_id="T-1",
        from_agent=CONVERSATION_INTELLIGENCE,
        to_agent=ARCHITECTURE_GUARDIAN,
        stage="architecture_review",
        payload={"intent": "review"},
        produced_at="2026-01-01T00:00:00Z",
    )
    defaults.update(overrides)
    return Handoff(**defaults)


def test_valid_handoff_constructs():
    handoff = _make()
    assert handoff.contract_version == "v1"
    assert handoff.status == "pending"


def test_unknown_from_agent_rejected():
    with pytest.raises(AgentContractError):
        _make(from_agent="not_a_real_agent")


def test_unknown_to_agent_rejected():
    with pytest.raises(AgentContractError):
        _make(to_agent="not_a_real_agent")


def test_self_handoff_rejected():
    with pytest.raises(AgentContractError):
        _make(from_agent=MASTER_ORCHESTRATOR, to_agent=MASTER_ORCHESTRATOR)


def test_unknown_stage_rejected():
    with pytest.raises(AgentContractError):
        _make(stage="not_a_real_stage")


def test_non_dict_payload_rejected():
    with pytest.raises(AgentContractError):
        _make(payload="not a dict")


@pytest.mark.parametrize(
    "forbidden_key", ["fact", "accepted_fact", "verified_fact", "candidate_fact"]
)
def test_payload_cannot_smuggle_promoted_truth_status(forbidden_key):
    """Invariant 2 enforced at the Handoff layer: no payload may carry a
    Fact/AcceptedFact/VerifiedFact/CandidateFact key, regardless of value."""
    with pytest.raises(AgentContractError):
        _make(payload={forbidden_key: "the defendant is liable"})


def test_invariant_refs_must_be_ints_in_range():
    with pytest.raises(AgentContractError):
        _make(invariant_refs=(0,))
    with pytest.raises(AgentContractError):
        _make(invariant_refs=(11,))
    with pytest.raises(AgentContractError):
        _make(invariant_refs=("2",))


def test_invariant_refs_valid_range_accepted():
    handoff = _make(invariant_refs=(1, 2, 10))
    assert handoff.invariant_refs == (1, 2, 10)


def test_unknown_status_rejected():
    with pytest.raises(AgentContractError):
        _make(status="approved")


def test_rejected_status_requires_reason():
    with pytest.raises(AgentContractError):
        _make(status="rejected")
    handoff = _make(status="rejected", rejection_reason="violates invariant 3")
    assert handoff.status == "rejected"


def test_missing_handoff_id_rejected():
    with pytest.raises(AgentContractError):
        _make(handoff_id="")


def test_missing_produced_at_rejected():
    with pytest.raises(AgentContractError):
        _make(produced_at="")
