"""
MIZAN Agent Society v1 - Evidence/Provenance Agent

Validates that an Observation's ``ProvenanceRecord``
(``contracts/mizan_contracts/provenance_v1.py``) resolves, without gaps, to
a SHA-256-identified ``SourceArtifactRecord`` (Invariant 7: Complete
Reverse Traceability), and produces an ``EvidenceRecord`` -- never a Fact
or Accepted Fact.

This agent is a thin, honest wrapper around
``provenance_v1.trace_to_source_sha256``: it adds no new trust, no new
promotion path, and no bypass. Its only job is to turn a successful trace
into an agent-society-native result type that other agents (and Governed
Memory) can consume, and to turn a broken chain into an
``AgentContractError`` instead of letting an unrelated exception type leak
across the agent boundary.
"""
from __future__ import annotations

import dataclasses

from .errors import AgentContractError

try:
    from mizan_contracts.provenance_v1 import (
        ProvenanceRecord,
        SourceArtifactRecord,
        trace_to_source_sha256,
    )
except ImportError as exc:  # pragma: no cover - exercised only if contracts/ is not on sys.path
    raise ImportError(
        "EvidenceProvenanceAgent requires contracts/mizan_contracts on "
        "sys.path (see conftest.py)."
    ) from exc


@dataclasses.dataclass(frozen=True, kw_only=True)
class EvidenceRecord:
    """The Evidence stage of Invariant 2 (Observation != Evidence != Fact !=
    Accepted Fact). This class has no ``status``, ``to_fact()``, or
    ``to_accepted_fact()`` -- promoting an EvidenceRecord further is not
    something this agent's API surface permits, by construction, matching
    how ``canonical_v1.RawObservation`` is deliberately incomplete."""

    stable_locator: str
    source_sha256: str
    engine: str


class EvidenceProvenanceAgent:
    def resolve(
        self, provenance: ProvenanceRecord, source_artifact: SourceArtifactRecord
    ) -> EvidenceRecord:
        try:
            sha256 = trace_to_source_sha256(provenance, source_artifact)
        except Exception as exc:
            raise AgentContractError(f"Evidence resolution failed: {exc}") from exc
        return EvidenceRecord(
            stable_locator=provenance.stable_locator,
            source_sha256=sha256,
            engine=provenance.engine,
        )
