"""
MIZAN Provenance Contract v1

Implements docs/architecture/ARCHITECTURAL_INVARIANTS.md Invariant 6
(Evidence Resolution Does Not Create Truth) and Invariant 7 (Complete
Reverse Traceability).

A ProvenanceRecord documents exactly how one Observation was produced: by
which engine/model/settings, from which Source Artifact (identified by
SHA-256), at which Stable Locator. It carries no verification status, no
retrieval score, and no "accepted" flag of any kind -- those concepts do
not exist in this contract and cannot be smuggled in through its
constructor (AC-13; dataclasses reject unknown keyword arguments).

Reverse traceability path this contract makes structurally possible
(not yet an "Accepted Fact" chain -- see AC-14):

    Observation -> stable_locator -> document_version_id -> document_id
                -> source_artifact_id -> source_sha256

No module in this file may import, reference, or depend on any third-party
document-intelligence or retrieval engine (Docling, PaddleOCR, MinerU,
Qdrant, pgvector, or any other).
"""
from __future__ import annotations

import dataclasses
from typing import Optional

from .errors import ContractValidationError
from .identity_v1 import validate_sha256
from .stable_locator_v1 import validate_locator_component

CONTRACT_VERSION = "v1"

_REQUIRED_NON_EMPTY_FIELDS = (
    "source_artifact_id",
    "document_id",
    "document_version_id",
    "stable_locator",
    "engine",
    "engine_version",
    "extraction_timestamp",
    "extraction_method",
)


@dataclasses.dataclass(frozen=True, kw_only=True)
class ProvenanceRecord:
    """Everything needed to reproduce and reverse-trace one extraction.

    `model`/`model_version` are optional (an extraction method that does not
    use a model, e.g. a rule-based parser, may legitimately omit them), but
    `engine`/`engine_version`/`settings`/`source_sha256` are never optional
    for a machine-produced observation (AC-12): omitting them is a contract
    violation, not an acceptable gap.
    """

    contract_version: str = dataclasses.field(default=CONTRACT_VERSION, init=False)

    source_artifact_id: str
    source_sha256: str
    document_id: str
    document_version_id: str
    stable_locator: str

    engine: str
    engine_version: str
    settings: dict
    extraction_timestamp: str
    extraction_method: str

    model: Optional[str] = None
    model_version: Optional[str] = None
    confidence: Optional[float] = None

    page: Optional[int] = None
    bbox: Optional[tuple[float, float, float, float]] = None
    span_offsets: Optional[tuple[int, int]] = None

    def __post_init__(self) -> None:
        for field_name in _REQUIRED_NON_EMPTY_FIELDS:
            value = getattr(self, field_name)
            if value is None or value == "":
                raise ContractValidationError(
                    f"ProvenanceRecord.{field_name} is required and cannot be empty "
                    "(AC-12: reproducibility metadata must not be lost)."
                )
        validate_sha256(self.source_sha256)
        validate_locator_component(self.stable_locator, "span")
        if not isinstance(self.settings, dict):
            raise ContractValidationError("ProvenanceRecord.settings must be a dict.")
        if self.confidence is not None and not (0.0 <= self.confidence <= 1.0):
            raise ContractValidationError("ProvenanceRecord.confidence must be within [0.0, 1.0].")


@dataclasses.dataclass(frozen=True, kw_only=True)
class SourceArtifactRecord:
    """The terminal node of reverse traceability: a SHA-256-identified
    source artifact (Invariant 7). Deliberately minimal -- full source
    artifact metadata lives in the Identity Contract
    (`identity_v1.SourceArtifactIdentity`); this record exists so a
    provenance chain can resolve to a SHA-256 without importing the full
    identity model, keeping the two contracts independently usable.
    """

    contract_version: str = dataclasses.field(default=CONTRACT_VERSION, init=False)
    source_artifact_id: str
    sha256: str

    def __post_init__(self) -> None:
        if not self.source_artifact_id:
            raise ContractValidationError("source_artifact_id is required and cannot be empty.")
        validate_sha256(self.sha256)


def trace_to_source_sha256(
    provenance: ProvenanceRecord, source_artifact: SourceArtifactRecord
) -> str:
    """Walk the structural reverse-traceability path from a provenance
    record to its source artifact's SHA-256 (AC-11, AC-14).

    This proves the STRUCTURAL path:
        Observation (via its stable_locator) -> ProvenanceRecord
            -> source_artifact_id -> SourceArtifactRecord -> sha256

    It does NOT prove an "Accepted Fact -> ... -> SHA-256" chain: Candidate
    Fact / Verification / Accepted Fact layers do not exist yet (see
    docs/architecture/ARCHITECTURAL_INVARIANTS.md Invariant 7 and AC-14).
    Raises ContractValidationError if the provenance record's
    source_artifact_id does not match the given source artifact (a broken
    link must fail loudly, never guess).
    """
    if provenance.source_artifact_id != source_artifact.source_artifact_id:
        raise ContractValidationError(
            "Broken provenance chain: ProvenanceRecord.source_artifact_id "
            f"({provenance.source_artifact_id!r}) does not match "
            f"SourceArtifactRecord.source_artifact_id ({source_artifact.source_artifact_id!r})."
        )
    if provenance.source_sha256 != source_artifact.sha256:
        raise ContractValidationError(
            "Broken provenance chain: ProvenanceRecord.source_sha256 does not "
            "match the resolved SourceArtifactRecord.sha256."
        )
    return source_artifact.sha256
