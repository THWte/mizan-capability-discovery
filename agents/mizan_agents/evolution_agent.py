"""
MIZAN Agent Society v1 - Evolution Agent

Proposes architecture amendments as structured, pending records in
Governed Memory. This agent cannot edit
``docs/architecture/ARCHITECTURAL_INVARIANTS.md`` or any ADR file, and
cannot mark its own proposal as adopted -- ``ARCHITECTURAL_INVARIANTS.md``
states it "is itself subject to amendment only via a new ADR that
explicitly supersedes or amends specific sections -- it is not edited
silently." This agent's API surface makes that structurally true: it has
no file-write capability and no ``status`` other than ``"proposed"``.
"""
from __future__ import annotations

import dataclasses

from .errors import AgentContractError
from .memory import GovernedMemory
from .registry import EVOLUTION_AGENT


@dataclasses.dataclass(frozen=True, kw_only=True)
class ProposedAmendment:
    proposal_id: str
    title: str
    rationale: str
    affected_invariants: tuple[int, ...]
    status: str = "proposed"

    def __post_init__(self) -> None:
        if not self.proposal_id or not self.title or not self.rationale:
            raise AgentContractError("proposal_id, title, and rationale are all required.")
        for ref in self.affected_invariants:
            if not isinstance(ref, int) or not (1 <= ref <= 10):
                raise AgentContractError(
                    f"affected_invariants entries must be ints in 1..10, got {ref!r}."
                )
        if self.status != "proposed":
            raise AgentContractError(
                "EvolutionAgent can only create proposals with status="
                "'proposed'. ARCHITECTURAL_INVARIANTS.md can only be amended "
                "via a new, human-authored ADR -- this agent cannot adopt its "
                "own proposal."
            )


class EvolutionAgent:
    def propose(
        self,
        memory: GovernedMemory,
        *,
        proposal_id: str,
        title: str,
        rationale: str,
        affected_invariants: tuple[int, ...],
        written_at: str,
    ) -> ProposedAmendment:
        amendment = ProposedAmendment(
            proposal_id=proposal_id,
            title=title,
            rationale=rationale,
            affected_invariants=affected_invariants,
        )
        memory.write(
            key=f"{EVOLUTION_AGENT}/proposal/{proposal_id}",
            value=dataclasses.asdict(amendment),
            written_by=EVOLUTION_AGENT,
            written_at=written_at,
        )
        return amendment
