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
"""
from __future__ import annotations

import dataclasses
from pathlib import Path

from .errors import AgentContractError

KNOWN_DECISIONS = ("REUSE", "EXTEND", "CONNECT", "INSPIRE", "REJECT")


@dataclasses.dataclass(frozen=True, kw_only=True)
class CapabilityRecord:
    capability_name: str
    decision: str
    evidence_doc: str

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


class CapabilityDiscoveryAgent:
    def __init__(self, repo_root: Path) -> None:
        self._repo_root = Path(repo_root)
        self._records: list[CapabilityRecord] = []

    def record_decision(
        self, *, capability_name: str, decision: str, evidence_doc: str
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
            capability_name=capability_name, decision=decision, evidence_doc=evidence_doc
        )
        self._records.append(record)
        return record

    def all_records(self) -> tuple[CapabilityRecord, ...]:
        return tuple(self._records)
