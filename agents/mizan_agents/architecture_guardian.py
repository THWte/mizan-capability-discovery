"""
MIZAN Agent Society v1 - Architecture Guardian Agent

The only agent empowered to approve a ``Handoff`` against
``docs/architecture/ARCHITECTURAL_INVARIANTS.md``. A PASS verdict from this
agent is the Master Orchestrator's sole gate for marking a task complete
(see ``orchestrator.MasterOrchestrator.complete``).

This agent checks the handoff's *payload shape* against specific,
checkable invariant violations. It intentionally does not try to be a
general-purpose policy engine: each check below cites exactly which
Invariant it enforces, matching the project-wide rule that an invariant
violation is never just "flagged for later" but blocks completion
outright.
"""
from __future__ import annotations

import dataclasses

from .errors import AgentContractError
from .handoff_contract import Handoff

try:
    from mizan_contracts.stable_locator_v1 import is_external_engine_identifier
except ImportError:  # pragma: no cover - exercised only if contracts/ is not on sys.path
    is_external_engine_identifier = None


@dataclasses.dataclass(frozen=True, kw_only=True)
class GuardianVerdict:
    handoff_id: str
    task_id: str
    verdict: str  # "PASS" | "FAIL"
    violated_invariants: tuple[int, ...] = ()
    reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.verdict not in ("PASS", "FAIL"):
            raise AgentContractError(f"Unknown verdict: {self.verdict!r}.")
        if self.verdict == "FAIL" and not self.reasons:
            raise AgentContractError("A FAIL verdict must carry at least one reason.")
        if self.verdict == "PASS" and self.violated_invariants:
            raise AgentContractError("A PASS verdict cannot carry violated_invariants.")


class ArchitectureGuardianAgent:
    def review(self, handoff: Handoff) -> GuardianVerdict:
        violated: list[int] = []
        reasons: list[str] = []
        payload = handoff.payload

        locator = payload.get("stable_locator")
        if locator is not None and is_external_engine_identifier is not None:
            if is_external_engine_identifier(locator):
                violated.append(3)
                reasons.append(
                    f"payload.stable_locator {locator!r} matches an external engine "
                    "identifier pattern (Invariant 3: MIZAN Owns Identity and "
                    "Stable Locators)."
                )

        if payload.get("becomes_load_bearing") is True:
            violated.append(10)
            reasons.append(
                "payload declares becomes_load_bearing=True: no engine may become "
                "architecturally load-bearing for MIZAN (Invariant 10: No Engine "
                "Becomes the System)."
            )

        if handoff.stage == "capability_evaluation" and 9 not in handoff.invariant_refs:
            violated.append(9)
            reasons.append(
                "capability_evaluation handoffs must cite Invariant 9 (Capability "
                "First, Technology Second) in invariant_refs."
            )

        if payload.get("retrieval_score") is not None and payload.get("treated_as_evidence") is True:
            violated.append(4)
            reasons.append(
                "payload treats a retrieval_score as evidence authority "
                "(Invariant 4: Retrieval != Evidence Authority)."
            )

        if payload.get("document_id") is not None and payload.get("source_artifact_id") is not None:
            if payload["document_id"] == payload["source_artifact_id"]:
                violated.append(5)
                reasons.append(
                    "payload.document_id equals payload.source_artifact_id "
                    "(Invariant 5: Document Identity != File Identity)."
                )

        verdict = "FAIL" if violated else "PASS"
        return GuardianVerdict(
            handoff_id=handoff.handoff_id,
            task_id=handoff.task_id,
            verdict=verdict,
            violated_invariants=tuple(violated),
            reasons=tuple(reasons),
        )
