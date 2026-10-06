"""
MIZAN Agent Society v1 - QA / Red-Team Agent

Deliberately attempts known-bad operations against the Handoff Contract and
Governed Memory, and reports whether the system actually rejected them. A
test suite that only exercises the "good path" can hide a regression; this
agent exists so adversarial coverage is itself a first-class, re-runnable
capability rather than a one-off manual check (matching the adversarial-
case discipline applied throughout the Core Contracts v1 review).
"""
from __future__ import annotations

import dataclasses
from typing import Callable

from .errors import AgentContractError
from .memory import GovernedMemory


@dataclasses.dataclass(frozen=True, kw_only=True)
class AttackResult:
    attack_name: str
    expected_to_be_rejected: bool
    was_rejected: bool

    @property
    def passed(self) -> bool:
        return self.expected_to_be_rejected == self.was_rejected


class QARedTeamAgent:
    def attempt_fact_smuggling_via_handoff(
        self, handoff_factory: Callable[..., object]
    ) -> AttackResult:
        """``handoff_factory`` must be a zero-arg callable that tries to
        construct a Handoff whose payload contains a forbidden key (e.g.
        ``{"fact": ...}``). A correctly-governed system raises
        ``AgentContractError`` from inside that callable."""
        try:
            handoff_factory()
            rejected = False
        except AgentContractError:
            rejected = True
        return AttackResult(
            attack_name="fact_smuggling_via_handoff",
            expected_to_be_rejected=True,
            was_rejected=rejected,
        )

    def attempt_memory_overwrite(
        self, memory: GovernedMemory, key: str, agent_role: str
    ) -> AttackResult:
        try:
            memory.write(
                key=key,
                value={"attempt": "overwrite"},
                written_by=agent_role,
                written_at="2026-01-01T00:00:00Z",
            )
            rejected = False
        except AgentContractError:
            rejected = True
        return AttackResult(
            attack_name="memory_overwrite",
            expected_to_be_rejected=True,
            was_rejected=rejected,
        )

    def attempt_cross_namespace_write(
        self, memory: GovernedMemory, agent_role: str, foreign_key: str
    ) -> AttackResult:
        try:
            memory.write(
                key=foreign_key,
                value={"x": 1},
                written_by=agent_role,
                written_at="2026-01-01T00:00:00Z",
            )
            rejected = False
        except AgentContractError:
            rejected = True
        return AttackResult(
            attack_name="cross_namespace_write",
            expected_to_be_rejected=True,
            was_rejected=rejected,
        )

    def attempt_engine_id_as_locator(self, checker: Callable[[str], bool], locator: str) -> AttackResult:
        """``checker`` is expected to be
        ``mizan_contracts.stable_locator_v1.is_external_engine_identifier``.
        A correctly-governed system returns True (i.e. it recognizes and
        would reject the engine-native id)."""
        return AttackResult(
            attack_name="engine_id_as_locator",
            expected_to_be_rejected=True,
            was_rejected=bool(checker(locator)),
        )
