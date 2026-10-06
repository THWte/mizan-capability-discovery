"""
MIZAN Agent Society v1.2 - Guardian Approval Registry

Closes the v1.2 "Approval Authenticity" gap: a ``GuardianApproval`` object
that is structurally well-formed -- correct ``task_id``,
``reviewed_handoff_id``, ``reviewed_payload_digest``, ``issued_by``, and a
``PASS`` ``verdict`` -- was still accepted by ``MasterOrchestrator.
complete()`` in v1.1 purely because its *fields happened to match* a real,
routed Handoff. Nothing proved the approval was ever produced by an
actual ``ArchitectureGuardianAgent`` review: ``canonical_digest`` is a
pure, public function, not a secret, so a caller able to read a routed
Handoff's payload could hand-construct a trusted-looking
``GuardianApproval`` for it without ever calling
``review()``/``approve()``.

This module closes that gap with an **issuance registry**, not
cryptography: ``register_from_guardian`` is the only write path, it
accepts a real ``Handoff`` -- never a pre-built verdict or approval -- and
it always re-runs the real review logic (``run_guardian_review``) itself,
live, against that exact Handoff. There is no parameter through which a
caller can hand over an already-decided outcome. ``MasterOrchestrator.
complete()`` then validates a caller-supplied ``GuardianApproval`` against
this registry's own stored record, field-for-field, rather than trusting
the caller-supplied object's fields in isolation (see ``validate()``).

No fake signature, secret, or token is used here, per the hardening
directive's explicit "NO FAKE CRYPTO" instruction -- Python has no true
access control, and a secret with no trust root to anchor to would be
security theater, not a real fix (see ``guardian_approval.py``'s existing
docstring for the same point, made in v1.1). The actual fix is
structural: a trusted approval can only ever be *minted* by this registry
actually running the review, so an approval that was never minted this
way is never found by ``validate()`` and is therefore always blocked --
regardless of how convincing its fields look.
"""
from __future__ import annotations

from .architecture_guardian import run_guardian_review
from .canonical_digest import canonical_digest
from .errors import AgentContractError
from .guardian_approval import GuardianApproval
from .handoff_contract import Handoff
from .registry import ARCHITECTURE_GUARDIAN

# PART "COVERAGE RULE" / "COMPLETION CONTEXT" (v1.2): a PARTIAL-coverage
# PASS only ever permits this one declared gate -- never full architecture
# certification. These constants exist so the distinction is enforced in
# code, not only prose (see docs/architecture/AGENT_SOCIETY.md
# "Amendment v1.2"). Nothing in this skeleton may claim
# ``FULL_ARCHITECTURE_CERTIFICATION`` -- there is no implementation of it.
ARCHITECTURE_GATE_V1 = "architecture_gate_v1"
FULL_ARCHITECTURE_CERTIFICATION = "full_architecture_certification"

#: The only completion scope this registry/society can currently vouch
#: for.
COMPLETION_SCOPE = ARCHITECTURE_GATE_V1


class GuardianApprovalRegistry:
    """The sole source of truth for which ``GuardianApproval`` records
    were genuinely produced by a live Architecture Guardian review.

    Public, limited interface only: ``register_from_guardian`` (the only
    writer), ``validate`` and ``lookup`` (read-only checks), and
    ``mark_consumed`` (replay bookkeeping). There is no setter that lets a
    caller store an arbitrary pre-built record.
    """

    def __init__(self) -> None:
        self._records: dict[str, GuardianApproval] = {}
        self._consumed: set[tuple[str, str]] = set()

    def register_from_guardian(
        self, handoff: Handoff, *, approval_id: str, issued_at: str
    ) -> GuardianApproval:
        """The only write path. Takes a real ``Handoff`` -- never a
        pre-built verdict or approval -- and independently re-runs the
        real review logic and re-computes the digest itself, live, right
        now. A caller cannot hand this method an already-decided PASS; the
        only thing it can influence is *which Handoff* gets reviewed, and
        the outcome for that Handoff is whatever
        ``run_guardian_review`` actually decides (PART "M8" /
        AC-12.4: there is no API here for writing an arbitrary verdict).
        """
        if not isinstance(handoff, Handoff):
            raise AgentContractError(
                "register_from_guardian requires a real Handoff object; a "
                "pre-built GuardianVerdict or GuardianApproval is not "
                "accepted here -- a trusted approval can only be produced "
                "from a live review of a real Handoff."
            )
        if not approval_id:
            raise AgentContractError("approval_id is required.")
        if approval_id in self._records:
            raise AgentContractError(
                f"approval_id {approval_id!r} is already registered. Each "
                "issuance must use a fresh, unique approval_id."
            )
        verdict = run_guardian_review(handoff)
        digest = canonical_digest(handoff.payload)
        approval = GuardianApproval(
            approval_id=approval_id,
            task_id=handoff.task_id,
            reviewed_handoff_id=handoff.handoff_id,
            reviewed_payload_digest=digest,
            verdict=verdict.verdict,
            coverage=verdict.coverage,
            checked_invariants=verdict.checked_invariants,
            violated_invariants=verdict.violated_invariants,
            issued_by=ARCHITECTURE_GUARDIAN,
            issued_at=issued_at,
        )
        self._records[approval_id] = approval
        return approval

    def lookup(self, approval_id: str) -> GuardianApproval | None:
        """Read-only lookup by ``approval_id``. Returns ``None`` for an
        unknown id; callers that need a hard failure should use
        ``validate()`` instead."""
        return self._records.get(approval_id)

    def validate(self, approval: GuardianApproval) -> GuardianApproval:
        """Return the registry's own trusted record for
        ``approval.approval_id`` if, and only if, every field on
        ``approval`` matches that record exactly. Raises
        ``AgentContractError`` if the id was never issued through
        ``register_from_guardian`` (forged-from-scratch approval, M1/M3)
        or if any field has been altered relative to the real record
        (forged-by-mutation approval, M2/M4/M5). This is the authority
        check ``MasterOrchestrator.complete()`` relies on -- it never
        trusts an approval object's own fields in isolation.
        """
        if not isinstance(approval, GuardianApproval):
            raise AgentContractError("validate() requires a GuardianApproval object.")
        record = self._records.get(approval.approval_id)
        if record is None:
            raise AgentContractError(
                f"approval_id {approval.approval_id!r} was never issued "
                "through the Guardian Approval Registry. A structurally "
                "well-formed GuardianApproval that was never actually "
                "registered by a live Architecture Guardian review is not "
                "trusted (forged-approval defense, v1.2)."
            )
        mismatched = (
            record.task_id != approval.task_id
            or record.reviewed_handoff_id != approval.reviewed_handoff_id
            or record.reviewed_payload_digest != approval.reviewed_payload_digest
            or record.verdict != approval.verdict
            or record.coverage != approval.coverage
            or record.checked_invariants != approval.checked_invariants
            or record.violated_invariants != approval.violated_invariants
        )
        if mismatched:
            raise AgentContractError(
                f"approval_id {approval.approval_id!r} is registered, but "
                "the supplied GuardianApproval does not match the "
                "registry's trusted record field-for-field. A real "
                "approval_id may never be reused while altering any field "
                "(verdict-tampering / task-or-handoff-relabeling defense)."
            )
        return record

    def mark_consumed(self, approval_id: str, task_id: str) -> bool:
        """Record that ``approval_id`` completed ``task_id``.

        Returns ``True`` the first time this exact ``(approval_id,
        task_id)`` pair is consumed, ``False`` on any later call with the
        same pair.

        **REPLAY PROTECTION policy (explicit, documented, v1.2):**
        replaying the same approval to re-complete the SAME task it
        already completed is an idempotent no-op --
        ``MasterOrchestrator.complete()`` does not raise on it, matching
        ``is_complete()`` already being a no-op-safe set membership check.
        Replaying it against a DIFFERENT task is already blocked earlier,
        by the ``task_id`` match against the registry record inside
        ``complete()``/``validate()``, before this method is ever reached
        -- so cross-task replay is rejected, same-task replay is
        idempotent, and neither is "undefined behavior".
        """
        key = (approval_id, task_id)
        if key in self._consumed:
            return False
        self._consumed.add(key)
        return True
