"""
MIZAN Agent Society v1 - Guardian Approval

``GuardianApproval`` is the tamper-resistant binding between a reviewed
Handoff and the one piece of state ``MasterOrchestrator.complete()`` is
allowed to trust (PART 8-13 of the v1.1 hardening directive).

Why this exists: before this module, any caller could construct a Handoff
``from_agent="architecture_guardian"`` with ``status="accepted"`` and hand
it to the Master Orchestrator -- there was no check that an actual
``ArchitectureGuardianAgent.review()`` call had ever happened, nor that
the approval still matched the payload that was reviewed. That is a
forgeable approval path (hardening finding P4).

How this module closes that gap, without adding cryptographic signing
(which would be false security theater here -- there is no private key or
trust root in this skeleton to make a signature meaningful):

1. ``issued_by`` is checked against the single registry constant
   ``ARCHITECTURE_GUARDIAN`` -- not just "some string that looks like the
   role name".
2. ``reviewed_payload_digest`` must be a well-formed SHA-256 hex digest
   (64 lowercase hex chars), produced by ``canonical_digest.py``.
3. A ``GuardianApproval`` only has a "real" API path of construction via
   ``ArchitectureGuardianAgent.approve()`` (``architecture_guardian.py``),
   which computes the digest independently from the handoff being
   reviewed, rather than trusting a caller-supplied digest. Nothing stops
   a determined caller from importing this class directly and constructing
   one by hand -- Python offers no true access control -- but doing so
   produces an object that is *useless on its own*: ``MasterOrchestrator.
   complete()`` independently re-derives the digest from the actual Handoff
   object it finds in its own routing history for ``reviewed_handoff_id``
   and rejects the approval if that digest does not match. A hand-forged
   approval is therefore only accepted if it happens to carry the correct
   digest of a Handoff that genuinely exists, with the correct task, in the
   Orchestrator's own history -- at which point it is, by definition, no
   longer a forgery of anything meaningful.
"""
from __future__ import annotations

import dataclasses

from .errors import AgentContractError

_HEX_DIGITS = set("0123456789abcdef")


def _looks_like_sha256_hex(value: str) -> bool:
    return len(value) == 64 and all(ch in _HEX_DIGITS for ch in value)


@dataclasses.dataclass(frozen=True, kw_only=True)
class GuardianApproval:
    approval_id: str
    task_id: str
    reviewed_handoff_id: str
    reviewed_payload_digest: str
    verdict: str  # "PASS" | "FAIL"
    coverage: str  # "FULL" | "PARTIAL" | "NOT_APPLICABLE"
    checked_invariants: tuple[int, ...]
    violated_invariants: tuple[int, ...] = ()
    issued_by: str
    issued_at: str

    def __post_init__(self) -> None:
        # Local import to avoid a module-level circular import between
        # guardian_approval.py and registry.py (registry has no reason to
        # know about approvals).
        from .registry import ARCHITECTURE_GUARDIAN

        if not self.approval_id:
            raise AgentContractError("approval_id is required.")
        if not self.task_id:
            raise AgentContractError("task_id is required.")
        if not self.reviewed_handoff_id:
            raise AgentContractError("reviewed_handoff_id is required.")
        if self.issued_by != ARCHITECTURE_GUARDIAN:
            raise AgentContractError(
                f"GuardianApproval.issued_by must be {ARCHITECTURE_GUARDIAN!r}, "
                f"got {self.issued_by!r}. Only the Architecture Guardian may "
                "issue an approval."
            )
        if not _looks_like_sha256_hex(self.reviewed_payload_digest):
            raise AgentContractError(
                "reviewed_payload_digest must be a 64-character lowercase hex "
                "SHA-256 digest."
            )
        if self.verdict not in ("PASS", "FAIL"):
            raise AgentContractError(f"Unknown verdict: {self.verdict!r}.")
        if self.coverage not in ("FULL", "PARTIAL", "NOT_APPLICABLE"):
            raise AgentContractError(f"Unknown coverage: {self.coverage!r}.")
        if self.verdict == "FAIL" and not self.violated_invariants:
            raise AgentContractError(
                "A FAIL approval must carry at least one violated invariant."
            )
        if self.verdict == "PASS" and self.violated_invariants:
            raise AgentContractError(
                "A PASS approval cannot carry violated_invariants."
            )
        if not self.issued_at:
            raise AgentContractError("issued_at is required.")

    @property
    def permits_completion(self) -> bool:
        """Whether this approval, taken alone, permits
        ``MasterOrchestrator.complete()`` to proceed. A PASS verdict always
        permits completion in v1 regardless of coverage -- there is only
        one completion gate in v1, and it is satisfied by the invariants
        the Guardian actually checked (see ``coverage``/``checked_invariants``
        on ``GuardianVerdict`` for exactly which ones)."""
        return self.verdict == "PASS"
