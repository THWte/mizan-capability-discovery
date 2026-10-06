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
calling ``ArchitectureGuardianAgent.review()``. ``complete()`` was changed
to require an actual ``GuardianApproval`` object and independently
re-verify, at completion time, task/handoff/digest/verdict agreement
against the live routed Handoff.

**Hardening history (v1.2 -- Approval Authenticity).** v1.1's digest check
closed the "forge a Handoff" path, but left one gap open: a caller who
could read a routed Handoff's payload could compute its
``canonical_digest`` themselves (a pure, public function -- not a secret)
and hand-construct a *structurally valid* ``GuardianApproval`` whose
fields happened to match that real Handoff, without ever calling
``ArchitectureGuardianAgent.review()``/``approve()``. ``complete()`` now
additionally requires this Orchestrator's
``approval_registry.GuardianApprovalRegistry`` to recognize the supplied
approval's ``approval_id`` as one it itself minted -- by actually running
the review -- and to confirm every field on the supplied approval matches
that stored record exactly (see ``approval_registry.py``). An approval
that is merely "field-correct" but was never actually issued through the
registry is rejected, regardless of how convincing it looks.

There is no override, flag, or admin bypass for any of these checks.
"""
from __future__ import annotations

from .approval_registry import GuardianApprovalRegistry
from .canonical_digest import canonical_digest
from .errors import AgentContractError
from .guardian_approval import GuardianApproval
from .handoff_contract import Handoff
from .registry import ARCHITECTURE_GUARDIAN, KNOWN_AGENT_ROLES


class MasterOrchestrator:
    def __init__(self, approval_registry: GuardianApprovalRegistry) -> None:
        """``approval_registry`` is required (v1.2): there is no longer a
        default-constructed Orchestrator that can complete any task,
        because completion authority now lives in the registry, not in
        this class. Callers must wire an explicit
        ``GuardianApprovalRegistry`` instance (see ``approval_registry.py``
        for why this is a plain constructor dependency, not a global
        mutable singleton)."""
        self._history: list[Handoff] = []
        self._completed: set[str] = set()
        self._approval_registry = approval_registry

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

        v1.2 hardening (Approval Authenticity): completion no longer
        trusts the fields on the caller-supplied ``approval`` object in
        isolation. ``complete()`` first resolves ``approval`` against
        this Orchestrator's ``GuardianApprovalRegistry``: only an approval
        the registry itself minted -- by actually re-running the
        Guardian's review logic against a real Handoff, inside
        ``register_from_guardian`` -- is trusted. A caller-supplied
        approval whose ``approval_id`` was never issued this way, or whose
        fields were altered relative to the registry's record, is
        rejected outright regardless of how convincing it looks.

        Raises ``AgentContractError`` for any of: a task/approval
        mismatch, an approval_id unknown to the registry or whose fields
        were tampered with, a ``reviewed_handoff_id`` that does not
        resolve to a real routed Handoff for this task addressed to the
        Guardian, a payload digest mismatch between the registry's record
        and the handoff's *current* payload (TOCTOU block), or a verdict
        that does not permit completion. There is no override path, flag,
        or admin bypass for any of these.
        """
        if approval.task_id != task_id:
            raise AgentContractError(
                f"GuardianApproval.task_id {approval.task_id!r} does not match "
                f"the task being completed {task_id!r}. An approval for one "
                "task may never be used to complete another."
            )
        # Authority check (v1.2): trust only the registry's own stored
        # record, never the caller-supplied object's fields in isolation.
        record = self._approval_registry.validate(approval)
        reviewed = self._find_routed_handoff(record.reviewed_handoff_id)
        if reviewed is None:
            raise AgentContractError(
                f"reviewed_handoff_id {record.reviewed_handoff_id!r} does not "
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
        if live_digest != record.reviewed_payload_digest:
            raise AgentContractError(
                "Payload digest mismatch: the reviewed handoff's payload has "
                "changed since the Architecture Guardian reviewed it. "
                "Completion is blocked (mutate-after-review / TOCTOU)."
            )
        if not record.permits_completion:
            raise AgentContractError(
                "GuardianApproval verdict does not permit completion "
                f"(verdict={record.verdict!r})."
            )
        self._approval_registry.mark_consumed(record.approval_id, task_id)
        self._completed.add(task_id)

    def is_complete(self, task_id: str) -> bool:
        return task_id in self._completed
