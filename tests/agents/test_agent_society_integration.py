"""End-to-end integration test for the MIZAN Agent Society v1.

Exercises a realistic Handoff chain across multiple agents, including a
deliberately-failing path: a Handoff whose payload would violate an
Architectural Invariant must be rejected by the Architecture Guardian, and
that rejection must actually block ``MasterOrchestrator.complete()`` -- not
just produce a warning that is otherwise ignored.
"""
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


def test_clean_task_reaches_completion_through_full_chain():
    orchestrator = MasterOrchestrator()
    conv_agent = ConversationIntelligenceAgent()
    guardian = ArchitectureGuardianAgent()
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

    # 4. Architecture Guardian reviews and accepts.
    verdict = guardian.review(intake)
    assert verdict.verdict == "PASS"

    approval = Handoff(
        handoff_id="H-100-2",
        task_id=task_id,
        from_agent=ARCHITECTURE_GUARDIAN,
        to_agent=MASTER_ORCHESTRATOR,
        stage="complete",
        payload={"verdict": verdict.verdict},
        status="accepted",
        produced_at="t2",
    )
    orchestrator.route(approval)

    # 5. Orchestrator can now mark the task complete.
    orchestrator.complete(task_id)
    assert orchestrator.is_complete(task_id)

    # 6. The Guardian's PASS verdict is recorded in Governed Memory for audit.
    memory.write(
        key=f"{ARCHITECTURE_GUARDIAN}/verdict/{task_id}",
        value={"verdict": verdict.verdict, "violated_invariants": list(verdict.violated_invariants)},
        written_by=ARCHITECTURE_GUARDIAN,
        written_at="t3",
    )
    assert memory.read(f"{ARCHITECTURE_GUARDIAN}/verdict/{task_id}").value["verdict"] == "PASS"


def test_invariant_violating_task_is_blocked_from_completion():
    """The deliberately-failing path: a handoff that disguises an engine-
    native locator as a MIZAN stable locator must be rejected by the
    Guardian, and the orchestrator must refuse to complete the task -- with
    no override."""
    orchestrator = MasterOrchestrator()
    guardian = ArchitectureGuardianAgent()

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

    verdict = guardian.review(bad_intake)
    assert verdict.verdict == "FAIL"
    assert 3 in verdict.violated_invariants

    rejection = Handoff(
        handoff_id="H-200-2",
        task_id=task_id,
        from_agent=ARCHITECTURE_GUARDIAN,
        to_agent=MASTER_ORCHESTRATOR,
        stage="complete",
        payload={"verdict": verdict.verdict},
        status="rejected",
        rejection_reason="; ".join(verdict.reasons),
        produced_at="t2",
    )
    orchestrator.route(rejection)

    assert not orchestrator.is_architecture_approved(task_id)
    try:
        orchestrator.complete(task_id)
        raised = False
    except AgentContractError:
        raised = True
    assert raised, "Orchestrator must not complete a task the Guardian rejected."
    assert not orchestrator.is_complete(task_id)


def test_approval_for_one_task_does_not_leak_to_another_in_full_chain():
    orchestrator = MasterOrchestrator()
    guardian = ArchitectureGuardianAgent()

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
    verdict = guardian.review(handoff)
    approval = Handoff(
        handoff_id="H-300-2",
        task_id=approved_task,
        from_agent=ARCHITECTURE_GUARDIAN,
        to_agent=MASTER_ORCHESTRATOR,
        stage="complete",
        payload={"verdict": verdict.verdict},
        status="accepted",
        produced_at="t2",
    )
    orchestrator.route(approval)
    orchestrator.complete(approved_task)

    assert orchestrator.is_complete(approved_task)
    assert not orchestrator.is_complete(other_task)
    try:
        orchestrator.complete(other_task)
        raised = False
    except AgentContractError:
        raised = True
    assert raised
