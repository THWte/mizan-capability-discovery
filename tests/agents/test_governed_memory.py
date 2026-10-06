"""Tests for MIZAN Agent Society v1 Governed Memory."""
import pytest

from mizan_agents.errors import AgentContractError
from mizan_agents.memory import GovernedMemory
from mizan_agents.registry import ARCHITECTURE_GUARDIAN, EVOLUTION_AGENT


def test_agent_can_write_its_own_namespace():
    memory = GovernedMemory()
    entry = memory.write(
        key=f"{ARCHITECTURE_GUARDIAN}/verdict/T-1",
        value={"verdict": "PASS"},
        written_by=ARCHITECTURE_GUARDIAN,
        written_at="2026-01-01T00:00:00Z",
    )
    assert entry.version == 1
    assert memory.read(f"{ARCHITECTURE_GUARDIAN}/verdict/T-1").value == {"verdict": "PASS"}


def test_agent_can_write_shared_namespace():
    memory = GovernedMemory()
    memory.write(
        key="shared/task/T-1",
        value={"status": "in_progress"},
        written_by=EVOLUTION_AGENT,
        written_at="2026-01-01T00:00:00Z",
    )
    assert memory.read("shared/task/T-1").written_by == EVOLUTION_AGENT


def test_agent_cannot_write_foreign_namespace():
    memory = GovernedMemory()
    with pytest.raises(AgentContractError):
        memory.write(
            key=f"{ARCHITECTURE_GUARDIAN}/verdict/T-1",
            value={"verdict": "PASS"},
            written_by=EVOLUTION_AGENT,
            written_at="2026-01-01T00:00:00Z",
        )


def test_unknown_writer_role_rejected():
    memory = GovernedMemory()
    with pytest.raises(AgentContractError):
        memory.write(
            key="shared/x",
            value={"a": 1},
            written_by="not_a_real_agent",
            written_at="2026-01-01T00:00:00Z",
        )


def test_unnamespaced_key_rejected():
    memory = GovernedMemory()
    with pytest.raises(AgentContractError):
        memory.write(
            key="no_slash_here",
            value={"a": 1},
            written_by=EVOLUTION_AGENT,
            written_at="2026-01-01T00:00:00Z",
        )


def test_write_is_append_only_overwrite_rejected():
    memory = GovernedMemory()
    memory.write(
        key="shared/x", value={"a": 1}, written_by=EVOLUTION_AGENT, written_at="t1"
    )
    with pytest.raises(AgentContractError):
        memory.write(
            key="shared/x", value={"a": 2}, written_by=EVOLUTION_AGENT, written_at="t2"
        )
    # Original value survives untouched.
    assert memory.read("shared/x").value == {"a": 1}


@pytest.mark.parametrize(
    "forbidden_key", ["fact", "accepted_fact", "verified_fact", "candidate_fact"]
)
def test_write_rejects_promoted_truth_status_value(forbidden_key):
    memory = GovernedMemory()
    with pytest.raises(AgentContractError):
        memory.write(
            key="shared/x",
            value={forbidden_key: "the defendant is liable"},
            written_by=EVOLUTION_AGENT,
            written_at="t1",
        )


def test_read_missing_key_raises():
    memory = GovernedMemory()
    with pytest.raises(AgentContractError):
        memory.read("shared/does_not_exist")


def test_audit_log_is_complete_and_ordered():
    memory = GovernedMemory()
    memory.write(key="shared/a", value={"n": 1}, written_by=EVOLUTION_AGENT, written_at="t1")
    memory.write(
        key=f"{ARCHITECTURE_GUARDIAN}/b",
        value={"n": 2},
        written_by=ARCHITECTURE_GUARDIAN,
        written_at="t2",
    )
    log = memory.audit_log()
    assert [entry.key for entry in log] == ["shared/a", f"{ARCHITECTURE_GUARDIAN}/b"]
    assert [entry.version for entry in log] == [1, 2]


def test_audit_log_cannot_be_mutated_to_affect_memory():
    memory = GovernedMemory()
    memory.write(key="shared/a", value={"n": 1}, written_by=EVOLUTION_AGENT, written_at="t1")
    log = memory.audit_log()
    assert isinstance(log, tuple)  # immutable sequence type returned
