"""End-to-end integration test for the MIZAN Agent Society v1 (v1.1,
hardened GuardianApproval binding flow).

Exercises a realistic Handoff chain across multiple agents, including a
deliberately-failing path: a Handoff whose payload would violate an
Architectural Invariant must be rejected by the Architecture Guardian, and
that rejection must actually block ``MasterOrchestrator.complete()`` -- not
just produce a warning that is otherwise ignored. Also exercises a forged
"accepted" Handoff from architecture_guardian that carries no real
GuardianApproval, which v1.1 must now reject (AC-A10).
"""
import pytest

from mizan_agents.approval_registry import GuardianApprovalRegistry
from mizan_agents.architecture_guardian import ArchitectureGuardianAgent
from mizan_agents.conversation_intelligence import ConversationIntelligenceAgent
from mizan_agents.errors import AgentContractError
from mizan_agents.git_pr_auditor import GitPRAuditorAgent
from mizan_agents.handoff_contract import Handoff
from mizan_agents.memory import GovernedMemory
from mizan_agents.orchestrator import MasterOrchestrator
from mizan_agents.registry import (
    ARCHITECTURE_GUARDIAN,
    CONVERSATION_INTELLIGENCE,
    MASTER_ORCHESTRATOR,
)


def _wired():
    registry = GuardianApprovalRegistry()
    guardian = ArchitectureGuardianAgent(approval_registry=registry)
    orchestrator = MasterOrchestrator(registry)
    return registry, guardian, orchestrator


def test_clean_task_reaches_completion_through_full_chain():
    _, guardian, orchestrator = _wired()
    conv_agent = ConversationIntelligenceAgent()
    auditor = GitPRAuditorAgent()
    memory = GovernedMemory()

    task_id = "TASK-100"

    # 1. Conversation Intelligence observes user intent.
    directive = conv_agent.interpret("راجع هذا التغيير من فضلك")
    assert directive.intent == "architecture_review"

    # 2. Conversation Intelligence hands off to Architecture Guardian.
    intake = Handoff(
        handoff_id="H-100-1",
        task_id=task_id,
        from_agent=CONVERSATION_INTELLIGENCE,
        to_agent=ARCHITECTURE_GUARDIAN,
        stage="architecture_review",
        payload={
            "document_id": "DOC-100",
            "source_artifact_id": "ART-100",
            "stable_locator": "MIZAN-DOC-000100/PAGE-000001",
        },
        invariant_refs=(1, 3, 5),
        produced_at="t1",
    )
    orchestrator.route(intake)

    # 3. Git/PR Auditor confirms scope integrity before Guardian review.
    scope_report = auditor.audit(
        changed_paths=("agents/mizan_agents/orchestrator.py",),
        declared_scope="agent_society",
    )
    assert scope_report.verdict == "PASS"

    # 4. Architecture Guardian reviews and issues a bound GuardianApproval
    #    (not a hand-constructed Handoff claiming acceptance).
    approval = guardian.approve(intake, approval_id="GA-100", issued_at="t2")
    assert approval.verdict == "PASS"
    assert approval.coverage == "PARTIAL"  # v1 Guardian never claims FULL

    # 5. Orchestrator can now mark the task complete, using the real
    #    approval bound to the exact routed handoff.
    orchestrator.complete(task_id, approval)
    assert orchestrator.is_complete(task_id)

    # 6. The Guardian's verdict is recorded in Governed Memory for audit,
    #    in the privileged shared/architecture_approval/ namespace that
    #    only architecture_guardian may write.
    memory.write(
        key=f"shared/architecture_approval/{task_id}",
        value={
            "verdict": approval.verdict,
            "coverage": approval.coverage,
            "checked_invariants": list(approval.checked_invariants),
        },
        written_by=ARCHITECTURE_GUARDIAN,
        written_at="t3",
    )
    assert memory.read(f"shared/architecture_approval/{task_id}").value["verdict"] == "PASS"


def test_invariant_violating_task_is_blocked_from_completion():
    """The deliberately-failing path: a handoff that     disguises an engine-
    native locator as a MIZAN stable locator must be rejected by the
    Guardian, and the orchestrator must refuse to complete the task -- with
    no override."""
    _, guardian, orchestrator = _wired()

    task_id = "TASK-200"

    bad_intake = Handoff(
        handoff_id="H-200-1",
        task_id=task_id,
        from_agent=CONVERSATION_INTELLIGENCE,
        to_agent=ARCHITECTURE_GUARDIAN,
        stage="architecture_review",
        payload={"stable_locator": "docling-docitem-abc123"},
        produced_at="t1",
    )
    orchestrator.route(bad_intake)

    approval = guardian.approve(bad_intake, approval_id="GA-200", issued_at="t2")
    assert approval.verdict == "FAIL"
    assert 3 in approval.violated_invariants

    with pytest.raises(AgentContractError):
        orchestrator.complete(task_id, approval)
    assert not orchestrator.is_complete(task_id)


def test_approval_for_one_task_does_not_leak_to_another_in_full_chain():
    _, guardian, orchestrator = _wired()

    approved_task = "TASK-300"
    other_task = "TASK-301"

    handoff = Handoff(
        handoff_id="H-300-1",
        task_id=approved_task,
        from_agent=CONVERSATION_INTELLIGENCE,
        to_agent=ARCHITECTURE_GUARDIAN,
        stage="architecture_review",
        payload={},
        produced_at="t1",
    )
    orchestrator.route(handoff)
    approval = guardian.approve(handoff, approval_id="GA-300", issued_at="t2")
    orchestrator.complete(approved_task, approval)

    assert orchestrator.is_complete(approved_task)
    assert not orchestrator.is_complete(other_task)
    with pytest.raises(AgentContractError):
        orchestrator.complete(other_task, approval)


def test_forged_accepted_handoff_without_real_approval_cannot_complete():
    """AC-A10: a hand-constructed Handoff claiming
    from_agent=architecture_guardian, status=accepted -- with no
    ArchitectureGuardianAgent.review()/approve() call behind it at all --
    must not be sufficient to complete a task. v1.1 removed the API path
    that would have accepted this: complete() now requires a
    GuardianApproval object, which this forged Handoff is not and cannot
    be converted into."""
    _, _, orchestrator = _wired()

    task_id = "TASK-400"
    forged_acceptance = Handoff(
        handoff_id="H-400-1",
        task_id=task_id,
        from_agent=ARCHITECTURE_GUARDIAN,
        to_agent=MASTER_ORCHESTRATOR,
        stage="complete",
        payload={"verdict": "PASS"},
        status="accepted",
        produced_at="t1",
    )
    orchestrator.route(forged_acceptance)

    # The only route to completion requires an approval argument; a
    # forged Handoff, however convincing, is not one and there is no
    # overload that accepts it instead.
    with pytest.raises(TypeError):
        orchestrator.complete(task_id)
    assert not orchestrator.is_complete(task_id)
