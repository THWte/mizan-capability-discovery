"""
MIZAN Agent Society v1 - Master Orchestrator

Routes ``Handoff`` instances between agents and is the only component that
may mark a task "complete". Completion requires a live, matching
``GuardianApproval`` (``guardian_approval.py``) -- the Orchestrator cannot
bypass this gate for its own convenience. This generalizes Invariant 1
(MIZAN Contract Before Engine) into "Gate Before Completion": no amount of
orchestration convenience is allowed to skip the one agent empowered to
check architectural compliance.

**Hardening history (v1.1).** The original ``complete(task_id)`` checked
only for *any* routed ``Handoff`` with ``from_agent="architecture_guardian"``
and ``status="accepted"`` for that ``task_id``. That is forgeable: nothing
stopped a caller from constructing such a Handoff by hand without ever
calling ``ArchitectureGuardianAgent.review()``. ``complete()`` now requires
an actual ``GuardianApproval`` object and independently re-verifies, at
completion time, that:

1. the approval's ``task_id`` matches the task being completed;
2. the approval was genuinely ``issued_by`` the Architecture Guardian;
3. the approval's ``reviewed_handoff_id`` resolves to a real ``Handoff``
   that was actually routed through this same Orchestrator, for this same
   task, addressed to the Architecture Guardian;
4. the reviewed handoff's *current* payload -- re-digested right now, not
   trusted from a stored value -- still matches the digest recorded on the
   approval (this is what blocks the PART 12 mutate-after-review attack);
5. the approval's verdict actually permits completion.

There is no override, flag, or admin bypass for any of these checks.
"""
from __future__ import annotations

from .canonical_digest import canonical_digest
from .errors import AgentContractError
from .guardian_approval import GuardianApproval
from .handoff_contract import Handoff
from .registry import ARCHITECTURE_GUARDIAN, KNOWN_AGENT_ROLES


class MasterOrchestrator:
    def __init__(self) -> None:
        self._history: list[Handoff] = []
        self._completed: set[str] = set()

    def route(self, handoff: Handoff) -> Handoff:
        """Accept a validated Handoff into the routing history.

        The Handoff Contract already validates ``to_agent``/``from_agent``
        at construction time; this re-check exists so a caller cannot
        construct a Handoff and then mutate the registry out from under
        the Orchestrator between construction and routing.
        """
        if handoff.to_agent not in KNOWN_AGENT_ROLES:
            raise AgentContractError(f"Cannot route to unknown agent {handoff.to_agent!r}.")
        self._history.append(handoff)
        return handoff

    def history_for_task(self, task_id: str) -> tuple[Handoff, ...]:
        return tuple(h for h in self._history if h.task_id == task_id)

    def _find_routed_handoff(self, handoff_id: str) -> Handoff | None:
        for handoff in self._history:
            if handoff.handoff_id == handoff_id:
                return handoff
        return None

    def is_architecture_approved(self, task_id: str) -> bool:
        """Legacy, intentionally weak signal retained only for
        introspection/observability -- it reflects whether *some* handoff
        claiming Guardian acceptance was routed, nothing more. It is never
        consulted by ``complete()`` and must not be used as a completion
        gate: see the class docstring for why that check was removed."""
        return any(
            h.task_id == task_id
            and h.from_agent == ARCHITECTURE_GUARDIAN
            and h.status == "accepted"
            for h in self._history
        )

    def complete(self, task_id: str, approval: GuardianApproval) -> None:
        """Mark ``task_id`` complete using a real, independently
        re-verified ``GuardianApproval``.

        Raises ``AgentContractError`` for any of: a task/approval
        mismatch, an approval not issued by the Architecture Guardian, a
        ``reviewed_handoff_id`` that does not resolve to a real routed
        Handoff for this task addressed to the Guardian, a payload digest
        mismatch between the approval and the handoff's current payload
        (TOCTOU block), or a verdict that does not permit completion.
        There is no override path, flag, or admin bypass for any of these.
        """
        if approval.task_id != task_id:
            raise AgentContractError(
                f"GuardianApproval.task_id {approval.task_id!r} does not match "
                f"the task being completed {task_id!r}. An approval for one "
                "task may never be used to complete another."
            )
        if approval.issued_by != ARCHITECTURE_GUARDIAN:
            raise AgentContractError(
                "GuardianApproval must be issued_by architecture_guardian."
            )
        reviewed = self._find_routed_handoff(approval.reviewed_handoff_id)
        if reviewed is None:
            raise AgentContractError(
                f"reviewed_handoff_id {approval.reviewed_handoff_id!r} does not "
                "resolve to any Handoff routed through this Orchestrator. A "
                "GuardianApproval not bound to a real, routed Handoff cannot "
                "complete a task."
            )
        if reviewed.task_id != task_id:
            raise AgentContractError(
                "The reviewed handoff's task_id does not match the task being "
                "completed."
            )
        if reviewed.to_agent != ARCHITECTURE_GUARDIAN:
            raise AgentContractError(
                "The reviewed handoff was not addressed to architecture_guardian."
            )
        live_digest = canonical_digest(reviewed.payload)
        if live_digest != approval.reviewed_payload_digest:
            raise AgentContractError(
                "Payload digest mismatch: the reviewed handoff's payload has "
                "changed since the Architecture Guardian reviewed it. "
                "Completion is blocked (mutate-after-review / TOCTOU)."
            )
        if not approval.permits_completion:
            raise AgentContractError(
                "GuardianApproval verdict does not permit completion "
                f"(verdict={approval.verdict!r})."
            )
        self._completed.add(task_id)

    def is_complete(self, task_id: str) -> bool:
        return task_id in self._completed
