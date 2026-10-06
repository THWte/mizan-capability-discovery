"""
MIZAN Agent Society v1 - Handoff Contract

The single mechanism by which any agent passes work to another. No agent
may call another agent's internals directly or mutate its state; every
inter-agent exchange is a ``Handoff`` instance, validated at construction
time, never after the fact.

Hard rule (generalizes Architectural Invariant 2, Observation != Evidence
!= Fact != Accepted Fact): a Handoff's ``payload`` may never carry a key
that represents a promoted truth status. This is enforced structurally in
``__post_init__`` below, not by convention or downstream review -- a
Handoff that tries to smuggle a ``fact``/``accepted_fact`` through the
agent-to-agent channel fails to construct at all.
"""
from __future__ import annotations

import dataclasses
from typing import Optional

from .errors import AgentContractError
from .registry import KNOWN_AGENT_ROLES

CONTRACT_VERSION = "v1"

KNOWN_STAGES = (
    "intake",
    "architecture_review",
    "capability_evaluation",
    "evidence_check",
    "adversarial_review",
    "scope_audit",
    "evolution_proposal",
    "complete",
)

KNOWN_STATUSES = ("pending", "accepted", "rejected")

# No handoff payload may carry a promoted truth status (Invariant 2).
FORBIDDEN_PAYLOAD_KEYS = ("fact", "accepted_fact", "verified_fact", "candidate_fact")


@dataclasses.dataclass(frozen=True, kw_only=True)
class Handoff:
    """One validated unit of agent-to-agent work.

    ``invariant_refs`` is the sender's explicit claim of which Architectural
    Invariants (1-10) this handoff was produced in compliance with. It is
    informational from the Handoff Contract's point of view -- the
    Architecture Guardian (``architecture_guardian.py``) is the agent that
    actually checks the claim against the payload.
    """

    contract_version: str = dataclasses.field(default=CONTRACT_VERSION, init=False)
    handoff_id: str
    task_id: str
    from_agent: str
    to_agent: str
    stage: str
    payload: dict
    invariant_refs: tuple[int, ...] = ()
    produced_at: str = ""
    status: str = "pending"
    rejection_reason: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.handoff_id:
            raise AgentContractError("handoff_id is required.")
        if not self.task_id:
            raise AgentContractError("task_id is required.")
        if self.from_agent not in KNOWN_AGENT_ROLES:
            raise AgentContractError(f"Unknown from_agent: {self.from_agent!r}.")
        if self.to_agent not in KNOWN_AGENT_ROLES:
            raise AgentContractError(f"Unknown to_agent: {self.to_agent!r}.")
        if self.from_agent == self.to_agent:
            raise AgentContractError("A handoff cannot target its own sender.")
        if self.stage not in KNOWN_STAGES:
            raise AgentContractError(f"Unknown stage: {self.stage!r}.")
        if not isinstance(self.payload, dict):
            raise AgentContractError("payload must be a dict.")
        for key in FORBIDDEN_PAYLOAD_KEYS:
            if key in self.payload:
                raise AgentContractError(
                    f"Handoff payload contains forbidden key {key!r}. No agent "
                    "handoff may carry a Fact/AcceptedFact/VerifiedFact/"
                    "CandidateFact -- an Observation cannot be promoted via the "
                    "Handoff Contract (Architectural Invariant 2)."
                )
        if not isinstance(self.invariant_refs, tuple):
            raise AgentContractError("invariant_refs must be a tuple of ints.")
        for ref in self.invariant_refs:
            if not isinstance(ref, int) or not (1 <= ref <= 10):
                raise AgentContractError(
                    f"invariant_refs entries must be ints in 1..10, got {ref!r}."
                )
        if self.status not in KNOWN_STATUSES:
            raise AgentContractError(f"Unknown status: {self.status!r}.")
        if self.status == "rejected" and not self.rejection_reason:
            raise AgentContractError("A rejected handoff must carry a rejection_reason.")
        if not self.produced_at:
            raise AgentContractError("produced_at is required.")
