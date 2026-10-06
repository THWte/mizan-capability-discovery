"""
MIZAN Agent Society v1 - Master Orchestrator

Routes ``Handoff`` instances between agents and is the only component that
may mark a task "complete". Completion requires an ACCEPTED handoff
produced by the Architecture Guardian for that same ``task_id`` -- the
Orchestrator cannot bypass this gate for its own convenience. This
generalizes Invariant 1 (MIZAN Contract Before Engine) into "Gate Before
Completion": no amount of orchestration convenience is allowed to skip the
one agent empowered to check architectural compliance.
"""
from __future__ import annotations

from .errors import AgentContractError
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

    def is_architecture_approved(self, task_id: str) -> bool:
        return any(
            h.task_id == task_id
            and h.from_agent == ARCHITECTURE_GUARDIAN
            and h.status == "accepted"
            for h in self._history
        )

    def complete(self, task_id: str) -> None:
        """Mark ``task_id`` complete.

        Raises ``AgentContractError`` if no ACCEPTED handoff from the
        Architecture Guardian exists for this task -- there is no override
        path, flag, or admin bypass for this check.
        """
        if not self.is_architecture_approved(task_id):
            raise AgentContractError(
                f"Cannot complete task {task_id!r}: no ACCEPTED handoff from "
                "architecture_guardian found. The Master Orchestrator may not "
                "mark a task complete without passing the architecture gate."
            )
        self._completed.add(task_id)

    def is_complete(self, task_id: str) -> bool:
        return task_id in self._completed
