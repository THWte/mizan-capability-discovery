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

**Hardening (v1.1, PART 19).** ``PROTECTED_TARGETS`` lists the exact
targets a proposal can never modify directly, regardless of how convincing
its rationale is: the Invariants document, ADRs, Core Contracts, agent
authority/permissions, and memory governance (ACLs, append-only
semantics). ``ProposedAmendment.requires_new_adr`` makes "any change here
needs a human-authored ADR, not an agent write" structurally true rather
than only documented in prose: the field exists specifically so it can
never be set to ``False`` -- there is no proposal shape, however phrased,
that bypasses the human-ADR gate.
"""
from __future__ import annotations

import dataclasses

from .errors import AgentContractError
from .memory import GovernedMemory
from .registry import EVOLUTION_AGENT

# Targets a ProposedAmendment can describe/recommend changes to, but can
# never itself apply. Any actual change to these requires a human-authored
# ADR and a human-merged PR -- never an agent write, regardless of how the
# proposal is worded or how strong its rationale appears.
PROTECTED_TARGETS = (
    "docs/architecture/ARCHITECTURAL_INVARIANTS.md",
    "docs/architecture/adr/",
    "contracts/mizan_contracts/",
    "agent_authority_and_permissions",
    "memory_governance_acls",
)


@dataclasses.dataclass(frozen=True, kw_only=True)
class ProposedAmendment:
    proposal_id: str
    title: str
    rationale: str
    affected_invariants: tuple[int, ...]
    status: str = "proposed"
    requires_new_adr: bool = True

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
        if not self.requires_new_adr:
            raise AgentContractError(
                "requires_new_adr cannot be False: a ProposedAmendment can "
                "never declare itself exempt from the human-ADR gate for "
                "PROTECTED_TARGETS (invariants, ADRs, Core Contracts, agent "
                "authority, memory governance)."
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
