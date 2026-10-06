"""Tests for the MIZAN Agent Society v1 QA/Red-Team Agent."""
from mizan_agents.handoff_contract import Handoff
from mizan_agents.memory import GovernedMemory
from mizan_agents.qa_redteam import QARedTeamAgent
from mizan_agents.registry import CONVERSATION_INTELLIGENCE, EVOLUTION_AGENT, ARCHITECTURE_GUARDIAN


def test_fact_smuggling_attack_is_rejected():
    agent = QARedTeamAgent()

    def bad_handoff_factory():
        return Handoff(
            handoff_id="H1",
            task_id="T1",
            from_agent=CONVERSATION_INTELLIGENCE,
            to_agent=ARCHITECTURE_GUARDIAN,
            stage="intake",
            payload={"fact": "the document is authentic"},
            produced_at="t1",
        )

    result = agent.attempt_fact_smuggling_via_handoff(bad_handoff_factory)
    assert result.passed is True
    assert result.was_rejected is True


def test_fact_smuggling_attack_fails_if_handoff_succeeds():
    agent = QARedTeamAgent()

    def permissive_handoff_factory():
        return Handoff(
            handoff_id="H1",
            task_id="T1",
            from_agent=CONVERSATION_INTELLIGENCE,
            to_agent=ARCHITECTURE_GUARDIAN,
            stage="intake",
            payload={"note": "ok"},
            produced_at="t1",
        )

    result = agent.attempt_fact_smuggling_via_handoff(permissive_handoff_factory)
    assert result.was_rejected is False
    assert result.passed is False


def test_memory_overwrite_attack_is_rejected():
    agent = QARedTeamAgent()
    memory = GovernedMemory()
    memory.write(
        key=f"{EVOLUTION_AGENT}/entry-1",
        value={"x": 1},
        written_by=EVOLUTION_AGENT,
        written_at="t0",
    )
    result = agent.attempt_memory_overwrite(
        memory, key=f"{EVOLUTION_AGENT}/entry-1", agent_role=EVOLUTION_AGENT
    )
    assert result.passed is True


def test_cross_namespace_write_attack_is_rejected():
    agent = QARedTeamAgent()
    memory = GovernedMemory()
    result = agent.attempt_cross_namespace_write(
        memory,
        agent_role=EVOLUTION_AGENT,
        foreign_key=f"{ARCHITECTURE_GUARDIAN}/fake-verdict",
    )
    assert result.passed is True


def test_engine_id_as_locator_attack_detected():
    agent = QARedTeamAgent()
    from mizan_contracts.stable_locator_v1 import is_external_engine_identifier

    result = agent.attempt_engine_id_as_locator(
        is_external_engine_identifier, "docling-docitem-4f2a"
    )
    assert result.passed is True
    assert result.was_rejected is True


def test_engine_id_as_locator_attack_fails_if_checker_is_blind():
    agent = QARedTeamAgent()
    result = agent.attempt_engine_id_as_locator(lambda _loc: False, "docling-docitem-4f2a")
    assert result.was_rejected is False
    assert result.passed is False
