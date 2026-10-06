"""
MIZAN Agent Society v1 - Capability Discovery Agent

Records capability-evaluation decisions that were already produced by the
sandbox/evaluation process described in ``docs/roadmap.md`` ("Process for
every integration"). This agent does **not** itself run engines,
benchmarks, or sandboxes, and it never re-evaluates a capability -- it only
accepts and structurally validates a decision that points at a real,
already-written evidence document in this repository.

This mirrors the project-wide rule enforced manually across the Docling
and PaddleOCR sandboxes: installation success is never capability success,
and a REUSE/EXTEND/CONNECT/INSPIRE/REJECT decision is never recorded
without a measurable, written evidence trail backing it.

**Hardening (v1.1, PART 18).** A benchmark decision (``decision``, e.g.
``CONNECT``) and a production-adoption lifecycle state
(``lifecycle_status``) are two different axes and must not be conflated --
exactly the PaddleOCR precedent, where the sandbox decision was ``CONNECT``
but ``Production Capability = NO`` until a human explicitly approved
production use. ``lifecycle_status`` ranges over ``DISCOVERED`` ->
``EVALUATED`` -> ``CANDIDATE`` -> ``APPROVED`` / ``REJECTED``; reaching
``APPROVED`` structurally requires a non-empty ``human_approval_reference``
(e.g. a merged PR URL or ADR id) -- there is no way to mark a capability
APPROVED on the strength of the sandbox decision alone. ``decision`` also
gained ``CONTINUE_BENCHMARKING`` for capabilities still under active,
inconclusive evaluation (neither a terminal adopt nor a terminal reject).
"""
from __future__ import annotations

import dataclasses
from pathlib import Path

from .errors import AgentContractError

KNOWN_DECISIONS = (
    "REUSE",
    "EXTEND",
    "CONNECT",
    "INSPIRE",
    "REJECT",
    "CONTINUE_BENCHMARKING",
)

LIFECYCLE_STATUSES = ("DISCOVERED", "EVALUATED", "CANDIDATE", "APPROVED", "REJECTED")

# A decision recorded with real evidence has, at minimum, been evaluated --
# so this is the correct default lifecycle_status for callers that don't
# explicitly reason about the lifecycle axis yet. It is never auto-promoted
# to APPROVED; that requires an explicit human_approval_reference.
_DEFAULT_LIFECYCLE_STATUS = "EVALUATED"


@dataclasses.dataclass(frozen=True, kw_only=True)
class CapabilityRecord:
    capability_name: str
    decision: str
    evidence_doc: str
    lifecycle_status: str = _DEFAULT_LIFECYCLE_STATUS
    human_approval_reference: str | None = None

    def __post_init__(self) -> None:
        if not self.capability_name:
            raise AgentContractError("capability_name is required.")
        if self.decision not in KNOWN_DECISIONS:
            raise AgentContractError(
                f"decision must be one of {KNOWN_DECISIONS}, got {self.decision!r}."
            )
        if not self.evidence_doc:
            raise AgentContractError(
                "evidence_doc is required: a capability decision without a "
                "pointer to real evaluation evidence is not recordable."
            )
        if self.lifecycle_status not in LIFECYCLE_STATUSES:
            raise AgentContractError(
                f"lifecycle_status must be one of {LIFECYCLE_STATUSES}, got "
                f"{self.lifecycle_status!r}."
            )
        if self.lifecycle_status == "APPROVED" and not self.human_approval_reference:
            raise AgentContractError(
                "lifecycle_status=APPROVED requires a non-empty "
                "human_approval_reference. A sandbox/benchmark decision "
                "(e.g. CONNECT) is never, by itself, sufficient for "
                "production adoption -- 'found capability' != 'adopted "
                "capability' (the PaddleOCR precedent: CONNECT decision, "
                "Production Capability = NO until explicit human approval)."
            )


class CapabilityDiscoveryAgent:
    def __init__(self, repo_root: Path) -> None:
        self._repo_root = Path(repo_root)
        self._records: list[CapabilityRecord] = []

    def record_decision(
        self,
        *,
        capability_name: str,
        decision: str,
        evidence_doc: str,
        lifecycle_status: str = _DEFAULT_LIFECYCLE_STATUS,
        human_approval_reference: str | None = None,
    ) -> CapabilityRecord:
        candidate = self._repo_root / evidence_doc
        if not candidate.is_file():
            raise AgentContractError(
                f"evidence_doc {evidence_doc!r} does not resolve to a real file "
                f"under {self._repo_root}. CapabilityDiscoveryAgent never records "
                "a decision without verifying its evidence document actually "
                "exists (mirrors: installation success != capability success)."
            )
        record = CapabilityRecord(
            capability_name=capability_name,
            decision=decision,
            evidence_doc=evidence_doc,
            lifecycle_status=lifecycle_status,
            human_approval_reference=human_approval_reference,
        )
        self._records.append(record)
        return record

    def all_records(self) -> tuple[CapabilityRecord, ...]:
        return tuple(self._records)
