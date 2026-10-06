"""Adversarial/hardening test suite for Agent Society v1.2 -- Approval
Authenticity Patch.

v1.1 closed "forge a Handoff" and "mutate payload after review" (see
``test_hardening_v1_1.py``). It left one gap: ``canonical_digest`` is a
pure, public function, not a secret. A caller who can read a routed
Handoff's payload can compute its digest themselves and hand-construct a
structurally valid ``GuardianApproval`` whose fields happen to match that
Handoff -- without ever calling ``ArchitectureGuardianAgent.review()`` or
``approve()``. v1.1's checks (task/handoff/digest/verdict agreement
against a live routed Handoff) do not catch this, because a forged
approval with the *correct* digest passes every one of them.

Each test below is labeled M1-M10 to match the v1.2 directive's attack
catalogue. The fix under test is ``agents/mizan_agents/
approval_registry.GuardianApprovalRegistry``: a trusted ``GuardianApproval``
can only be minted by ``register_from_guardian``, which always re-runs the
real review logic itself against a real ``Handoff`` -- never accepting a
caller-supplied verdict, digest, or approval as input. ``MasterOrchestrator.
complete()`` now validates the caller-supplied approval against the
registry's own stored record (see ``orchestrator.py``), not against the
approval object's fields in isolation.
"""
from __future__ import annotations

import pytest

from mizan_agents.approval_registry import (
    ARCHITECTURE_GATE_V1,
    COMPLETION_SCOPE,
    FULL_ARCHITECTURE_CERTIFICATION,
    GuardianApprovalRegistry,
)
from mizan_agents.architecture_guardian import ArchitectureGuardianAgent
from mizan_agents.canonical_digest import canonical_digest
from mizan_agents.errors import AgentContractError
from mizan_agents.guardian_approval import GuardianApproval
from mizan_agents.handoff_contract import Handoff
from mizan_agents.orchestrator import MasterOrchestrator
from mizan_agents.registry import ARCHITECTURE_GUARDIAN, CONVERSATION_INTELLIGENCE


def _wired():
    registry = GuardianApprovalRegistry()
    guardian = ArchitectureGuardianAgent(approval_registry=registry)
    orchestrator = MasterOrchestrator(registry)
    return registry, guardian, orchestrator


def _handoff(**overrides):
    defaults = dict(
        handoff_id="HO-V2",
        task_id="T-V2",
        from_agent=CONVERSATION_INTELLIGENCE,
        to_agent=ARCHITECTURE_GUARDIAN,
        stage="architecture_review",
        payload={},
        produced_at="t1",
    )
    defaults.update(overrides)
    return Handoff(**defaults)


# --- M1: FORGED OBJECT TEST -------------------------------------------------
# Correct digest, correct every other field, but an approval_id that was
# NEVER registered -- and the test asserts guardian.review()/approve() was
# never called to produce it. This is the exact v1.1 residual gap.


def test_m1_forged_approval_with_correct_digest_is_rejected():
    registry, guardian, orchestrator = _wired()
    handoff = _handoff(handoff_id="HO-M1", task_id="T-M1", payload={"value": "clean"})
    orchestrator.route(handoff)

    # Attacker computes the real digest themselves -- canonical_digest is a
    # pure, public function, not a secret -- without ever calling
    # guardian.review()/approve().
    forged_digest = canonical_digest(handoff.payload)
    forged = GuardianApproval(
        approval_id="GA-NEVER-REGISTERED",
        task_id="T-M1",
        reviewed_handoff_id="HO-M1",
        reviewed_payload_digest=forged_digest,
        verdict="PASS",
        coverage="PARTIAL",
        checked_invariants=(3, 4, 5, 10),
        issued_by=ARCHITECTURE_GUARDIAN,
        issued_at="t2",
    )
    # Confirm this is genuinely a forgery: the registry never saw it.
    assert registry.lookup("GA-NEVER-REGISTERED") is None

    with pytest.raises(AgentContractError):
        orchestrator.complete("T-M1", forged)
    assert not orchestrator.is_complete("T-M1")


# --- M2: verdict tampering via a reused, real approval_id -------------------
# Register a real FAIL approval, then try to "launder" it into a PASS by
# resubmitting the same approval_id with verdict flipped.


def test_m2_verdict_tampering_on_a_real_approval_id_is_rejected():
    registry, guardian, orchestrator = _wired()
    handoff = _handoff(
        handoff_id="HO-M2", task_id="T-M2", payload={"becomes_load_bearing": True}
    )
    orchestrator.route(handoff)
    real = guardian.approve(handoff, approval_id="GA-M2", issued_at="t2")
    assert real.verdict == "FAIL"

    tampered = GuardianApproval(
        approval_id="GA-M2",  # same, real, registered id
        task_id=real.task_id,
        reviewed_handoff_id=real.reviewed_handoff_id,
        reviewed_payload_digest=real.reviewed_payload_digest,
        verdict="PASS",  # flipped
        coverage=real.coverage,
        checked_invariants=real.checked_invariants,
        violated_invariants=(),
        issued_by=ARCHITECTURE_GUARDIAN,
        issued_at=real.issued_at,
    )
    with pytest.raises(AgentContractError):
        orchestrator.complete("T-M2", tampered)


# --- M3: never-registered approval_id, otherwise perfectly formed ----------


def test_m3_never_registered_approval_id_is_rejected_even_if_well_formed():
    registry, guardian, orchestrator = _wired()
    handoff = _handoff(handoff_id="HO-M3", task_id="T-M3")
    orchestrator.route(handoff)
    well_formed_but_unregistered = GuardianApproval(
        approval_id="GA-M3-GHOST",
        task_id="T-M3",
        reviewed_handoff_id="HO-M3",
        reviewed_payload_digest=canonical_digest(handoff.payload),
        verdict="PASS",
        coverage="PARTIAL",
        checked_invariants=(3, 4, 5, 10),
        issued_by=ARCHITECTURE_GUARDIAN,
        issued_at="t2",
    )
    assert registry.lookup("GA-M3-GHOST") is None
    with pytest.raises(AgentContractError):
        orchestrator.complete("T-M3", well_formed_but_unregistered)


# --- M4: cross-task reuse of a real, registered approval_id ----------------


def test_m4_real_approval_id_cannot_be_relabeled_to_a_different_task():
    registry, guardian, orchestrator = _wired()
    handoff = _handoff(handoff_id="HO-M4", task_id="T-M4-A")
    orchestrator.route(handoff)
    real = guardian.approve(handoff, approval_id="GA-M4", issued_at="t2")

    relabeled = GuardianApproval(
        approval_id="GA-M4",
        task_id="T-M4-B",  # different task
        reviewed_handoff_id=real.reviewed_handoff_id,
        reviewed_payload_digest=real.reviewed_payload_digest,
        verdict=real.verdict,
        coverage=real.coverage,
        checked_invariants=real.checked_invariants,
        issued_by=ARCHITECTURE_GUARDIAN,
        issued_at=real.issued_at,
    )
    with pytest.raises(AgentContractError):
        orchestrator.complete("T-M4-B", relabeled)


# --- M5: cross-handoff reuse of a real, registered approval_id -------------


def test_m5_real_approval_id_cannot_be_relabeled_to_a_different_handoff():
    registry, guardian, orchestrator = _wired()
    handoff_1 = _handoff(handoff_id="HO-M5-1", task_id="T-M5", payload={"a": 1})
    handoff_2 = _handoff(handoff_id="HO-M5-2", task_id="T-M5", payload={"a": 2})
    orchestrator.route(handoff_1)
    orchestrator.route(handoff_2)
    real = guardian.approve(handoff_1, approval_id="GA-M5", issued_at="t2")

    relabeled = GuardianApproval(
        approval_id="GA-M5",
        task_id=real.task_id,
        reviewed_handoff_id="HO-M5-2",  # different handoff
        reviewed_payload_digest=real.reviewed_payload_digest,
        verdict=real.verdict,
        coverage=real.coverage,
        checked_invariants=real.checked_invariants,
        issued_by=ARCHITECTURE_GUARDIAN,
        issued_at=real.issued_at,
    )
    with pytest.raises(AgentContractError):
        orchestrator.complete("T-M5", relabeled)


# --- M6: real, honestly-issued approval through the full chain -> PASS -----
# (control case: the fix must not break the legitimate path.)


def test_m6_real_approval_test_full_chain_succeeds():
    registry, guardian, orchestrator = _wired()
    handoff = _handoff(handoff_id="HO-M6", task_id="T-M6")
    orchestrator.route(handoff)
    approval = guardian.approve(handoff, approval_id="GA-M6", issued_at="t2")
    assert approval.verdict == "PASS"
    orchestrator.complete("T-M6", approval)
    assert orchestrator.is_complete("T-M6")
    # mark_consumed was recorded; replaying the same (approval_id, task_id)
    # is an idempotent no-op, not an error.
    assert registry.mark_consumed("GA-M6", "T-M6") is False


# --- M7: duplicate approval_id reuse rejected at registration time ---------


def test_m7_duplicate_approval_id_rejected_at_registration():
    registry, guardian, _ = _wired()
    handoff_1 = _handoff(handoff_id="HO-M7-1", task_id="T-M7-A")
    handoff_2 = _handoff(handoff_id="HO-M7-2", task_id="T-M7-B")
    guardian.approve(handoff_1, approval_id="GA-M7", issued_at="t2")
    with pytest.raises(AgentContractError):
        guardian.approve(handoff_2, approval_id="GA-M7", issued_at="t3")


# --- M8: direct registry write attempt bypassing a real Handoff -----------
# Python has no true access control (documented limitation, v1.1). The
# honest claim here is narrower and still real: register_from_guardian
# rejects any input that is not an actual Handoff object -- there is no
# parameter anywhere for injecting a pre-decided verdict/approval directly.


def test_m8_register_from_guardian_rejects_non_handoff_input():
    registry, _, _ = _wired()
    with pytest.raises(AgentContractError):
        registry.register_from_guardian(
            {"task_id": "T-M8", "verdict": "PASS"},  # not a Handoff
            approval_id="GA-M8",
            issued_at="t1",
        )
    with pytest.raises(AgentContractError):
        registry.register_from_guardian(
            None, approval_id="GA-M8-B", issued_at="t1"
        )


# --- M9: PARTIAL coverage can never be laundered into FULL certification --


def test_m9_partial_coverage_approval_cannot_claim_full_certification():
    registry, guardian, orchestrator = _wired()
    handoff = _handoff(handoff_id="HO-M9", task_id="T-M9")
    orchestrator.route(handoff)
    approval = guardian.approve(handoff, approval_id="GA-M9", issued_at="t2")
    assert approval.coverage == "PARTIAL"
    # The registry's own completion-scope constant is the narrow,
    # structural gate v1.2 can vouch for -- never the broader one.
    assert COMPLETION_SCOPE == ARCHITECTURE_GATE_V1
    assert COMPLETION_SCOPE != FULL_ARCHITECTURE_CERTIFICATION
    assert ARCHITECTURE_GATE_V1 != FULL_ARCHITECTURE_CERTIFICATION
    # Attempting to smuggle a FULL-coverage claim into a hand-relabeled
    # approval for the same real approval_id must still be rejected by
    # validate() (coverage mismatch is one of the compared fields).
    smuggled = GuardianApproval(
        approval_id="GA-M9",
        task_id=approval.task_id,
        reviewed_handoff_id=approval.reviewed_handoff_id,
        reviewed_payload_digest=approval.reviewed_payload_digest,
        verdict=approval.verdict,
        coverage="FULL",  # tampered: claims full certification
        checked_invariants=approval.checked_invariants,
        issued_by=ARCHITECTURE_GUARDIAN,
        issued_at=approval.issued_at,
    )
    with pytest.raises(AgentContractError):
        orchestrator.complete("T-M9", smuggled)


# --- M10: replay policy -- same (approval_id, task_id) is idempotent, ------
#          cross-task replay of a real approval_id is rejected (already
#          covered structurally by M4, asserted again here against the
#          registry's own mark_consumed bookkeeping directly).


def test_m10_replay_policy_same_task_idempotent_cross_task_rejected():
    registry, guardian, orchestrator = _wired()
    handoff = _handoff(handoff_id="HO-M10", task_id="T-M10")
    orchestrator.route(handoff)
    approval = guardian.approve(handoff, approval_id="GA-M10", issued_at="t2")
    orchestrator.complete("T-M10", approval)
    assert orchestrator.is_complete("T-M10")

    # Same-task replay: idempotent no-op, not an error.
    orchestrator.complete("T-M10", approval)
    assert orchestrator.is_complete("T-M10")

    # Cross-task replay of the same real approval_id: rejected.
    with pytest.raises(AgentContractError):
        orchestrator.complete("T-OTHER", approval)
    assert not orchestrator.is_complete("T-OTHER")


# --- Additional structural check: registry never exposes a public setter --


def test_registry_has_no_public_setter_besides_register_from_guardian():
    registry = GuardianApprovalRegistry()
    public_methods = {
        name
        for name in dir(registry)
        if not name.startswith("_") and callable(getattr(registry, name))
    }
    assert public_methods == {
        "register_from_guardian",
        "validate",
        "lookup",
        "mark_consumed",
    }
