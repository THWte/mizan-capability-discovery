"""
MIZAN Agent Society v1 - Architecture Guardian Agent

The only agent empowered to approve a ``Handoff`` against
``docs/architecture/ARCHITECTURAL_INVARIANTS.md``. A PASS verdict from this
agent, packaged into a ``GuardianApproval`` (``guardian_approval.py``), is
the Master Orchestrator's sole gate for marking a task complete (see
``orchestrator.MasterOrchestrator.complete``).

This agent checks the handoff's *payload shape* against specific,
checkable invariant violations. It intentionally does not try to be a
general-purpose policy engine: each check below cites exactly which
Invariant it enforces, matching the project-wide rule that an invariant
violation is never just "flagged for later" but blocks completion
outright.

**Coverage honesty (PART 6/7 of the v1.1 hardening directive).** This
Guardian checks a fixed, named subset of the 10 Architectural Invariants
-- never all 10. A ``PASS`` verdict therefore means "the invariants this
Guardian actually checked were satisfied", not "the full architecture was
certified". ``GuardianVerdict.coverage`` is always ``"PARTIAL"`` in v1 for
exactly this reason, and ``checked_invariants``/``unchecked_invariants``
make the boundary explicit and machine-readable so no caller can
mistake a scoped PASS for a full-architecture PASS.
"""
from __future__ import annotations

import dataclasses

from .canonical_digest import canonical_digest
from .errors import AgentContractError
from .handoff_contract import Handoff

try:
    from mizan_contracts.stable_locator_v1 import is_external_engine_identifier
except ImportError:  # pragma: no cover - exercised only if contracts/ is not on sys.path
    is_external_engine_identifier = None

# The full Architectural Invariant ID space (1..10, see
# docs/architecture/ARCHITECTURAL_INVARIANTS.md). Used only to compute
# ``unchecked_invariants`` -- this Guardian never claims to check all of
# them.
ALL_INVARIANTS = tuple(range(1, 11))

# Invariants this Guardian always checks, regardless of stage.
_ALWAYS_CHECKED_INVARIANTS = (3, 4, 5, 10)


@dataclasses.dataclass(frozen=True, kw_only=True)
class GuardianVerdict:
    handoff_id: str
    task_id: str
    verdict: str  # "PASS" | "FAIL" -- scoped to checked_invariants ONLY, see coverage
    coverage: str = "PARTIAL"  # "FULL" | "PARTIAL" | "NOT_APPLICABLE"
    checked_invariants: tuple[int, ...] = ()
    violated_invariants: tuple[int, ...] = ()
    unchecked_invariants: tuple[int, ...] = ()
    reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.verdict not in ("PASS", "FAIL"):
            raise AgentContractError(f"Unknown verdict: {self.verdict!r}.")
        if self.verdict == "FAIL" and not self.reasons:
            raise AgentContractError("A FAIL verdict must carry at least one reason.")
        if self.verdict == "PASS" and self.violated_invariants:
            raise AgentContractError("A PASS verdict cannot carry violated_invariants.")
        if self.coverage not in ("FULL", "PARTIAL", "NOT_APPLICABLE"):
            raise AgentContractError(f"Unknown coverage: {self.coverage!r}.")
        expected_unchecked = tuple(
            sorted(set(ALL_INVARIANTS) - set(self.checked_invariants))
        )
        if tuple(sorted(self.unchecked_invariants)) != expected_unchecked:
            raise AgentContractError(
                "unchecked_invariants must equal ALL_INVARIANTS minus "
                "checked_invariants -- a GuardianVerdict cannot misstate its "
                "own coverage."
            )
        if self.coverage == "FULL" and self.unchecked_invariants:
            raise AgentContractError(
                "coverage='FULL' cannot coexist with a non-empty "
                "unchecked_invariants -- that combination would claim full "
                "architecture certification while silently skipping "
                "invariants (PART 7: PASS != FULL ARCHITECTURE CERTIFICATION)."
            )

    @property
    def scoped_label(self) -> str:
        """Explicit, unambiguous label distinguishing a scoped check result
        from a full-architecture certification (PART 7). Prefer this over
        reading ``verdict`` alone when presenting results to a human or
        another agent."""
        if self.verdict == "FAIL":
            return "CHECKED_FAIL"
        return "PARTIAL_PASS" if self.coverage == "PARTIAL" else "CHECKED_PASS"


class ArchitectureGuardianAgent:
    def review(self, handoff: Handoff) -> GuardianVerdict:
        violated: list[int] = []
        reasons: list[str] = []
        payload = handoff.payload

        checked = set(_ALWAYS_CHECKED_INVARIANTS)
        if handoff.stage == "capability_evaluation":
            checked.add(9)

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
        checked_invariants = tuple(sorted(checked))
        unchecked_invariants = tuple(
            sorted(set(ALL_INVARIANTS) - set(checked_invariants))
        )
        return GuardianVerdict(
            handoff_id=handoff.handoff_id,
            task_id=handoff.task_id,
            verdict=verdict,
            coverage="PARTIAL",
            checked_invariants=checked_invariants,
            violated_invariants=tuple(violated),
            unchecked_invariants=unchecked_invariants,
            reasons=tuple(reasons),
        )

    def approve(self, handoff: Handoff, *, approval_id: str, issued_at: str):
        """Review ``handoff`` and package the result into a
        ``GuardianApproval`` bound to this exact payload via a canonical
        digest (PART 8/9). This is the only code path in the agent society
        meant to produce a ``GuardianApproval`` from a real review -- see
        ``guardian_approval.py`` for why a hand-constructed one is inert
        without a matching, live Handoff."""
        from .registry import ARCHITECTURE_GUARDIAN
        from .guardian_approval import GuardianApproval

        verdict = self.review(handoff)
        digest = canonical_digest(handoff.payload)
        return GuardianApproval(
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

