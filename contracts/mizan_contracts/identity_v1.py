"""
MIZAN Identity Contract v1

Implements docs/architecture/ARCHITECTURAL_INVARIANTS.md Invariant 5
(Document Identity != File Identity) and the identity half of Invariant 3
(MIZAN Owns Identity and Stable Locators) and Invariant 7 (Complete Reverse
Traceability -> SHA-256 Source Artifact).

Core rule
---------
SHA-256 identifies a *byte artifact* (a specific file as it existed at
ingestion time). `document_id` identifies a *logical document* (the legal
instrument/filing/contract MIZAN's domain cares about). These are never the
same field, never derived from one another automatically, and a
`SourceArtifactIdentity` can never silently become a `DocumentIdentity`.

Two different file bytes (two different SHA-256 values) MAY represent the
same logical document (e.g. a scanned PDF and a re-typed DOCX of the same
contract) -- but MIZAN never merges them automatically. Same-content
detection (`content_fingerprint`) only ever produces a *duplicate candidate*,
which requires an explicit MIZAN decision to confirm as the same document.

No module in this file may import, reference, or depend on any third-party
document-intelligence or retrieval engine (Docling, PaddleOCR, MinerU,
Qdrant, pgvector, or any other).
"""
from __future__ import annotations

import dataclasses
import re
from typing import Optional

from .errors import ContractValidationError

CONTRACT_VERSION = "v1"

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def validate_sha256(value: str) -> str:
    """Validate a SHA-256 hex digest: exactly 64 lowercase hex characters.

    Raises ContractValidationError for anything else, including missing
    values, wrong length, uppercase, or non-hex characters. Used by AC-04.
    """
    if not isinstance(value, str) or not _SHA256_RE.match(value):
        raise ContractValidationError(
            f"Invalid SHA-256 digest: {value!r}. Must be exactly 64 lowercase "
            "hexadecimal characters."
        )
    return value


@dataclasses.dataclass(frozen=True, kw_only=True)
class SourceArtifactIdentity:
    """Identity of a byte artifact (a specific file's exact bytes).

    This is NEVER a document identity. A `source_artifact_id` is a MIZAN-
    issued identifier for one ingested file; `sha256` is the cryptographic
    anchor for its bytes (Invariant 7); `content_fingerprint` is a *hint*
    for duplicate detection only (see `classify_duplicate_candidate`).
    """

    contract_version: str = dataclasses.field(default=CONTRACT_VERSION, init=False)
    source_artifact_id: str
    sha256: str
    content_fingerprint: str
    byte_size: int
    ingestion_timestamp: str

    def __post_init__(self) -> None:
        if not self.source_artifact_id:
            raise ContractValidationError("source_artifact_id is required and cannot be empty.")
        validate_sha256(self.sha256)
        if not self.content_fingerprint:
            raise ContractValidationError("content_fingerprint is required and cannot be empty.")
        if self.byte_size < 0:
            raise ContractValidationError("byte_size cannot be negative.")


@dataclasses.dataclass(frozen=True, kw_only=True)
class DocumentIdentity:
    """Identity of a logical document, distinct from any file artifact.

    `document_id` is assigned by MIZAN's identity layer and MUST NOT be
    derived deterministically from `source_artifact_id`/sha256 (Invariant 5):
    two different source artifacts can point at the same document_id, and
    a single source artifact never *defines* a document_id on its own.
    """

    contract_version: str = dataclasses.field(default=CONTRACT_VERSION, init=False)
    document_id: str
    source_artifact_ids: tuple[str, ...]
    version: int
    parent_version: Optional[int] = None
    source_provenance: str = ""

    def __post_init__(self) -> None:
        if not self.document_id:
            raise ContractValidationError("document_id is required and cannot be empty.")
        if not self.source_artifact_ids:
            raise ContractValidationError(
                "A DocumentIdentity must reference at least one source_artifact_id."
            )
        for sid in self.source_artifact_ids:
            if sid == self.document_id:
                raise ContractValidationError(
                    "document_id must never equal a source_artifact_id "
                    "(Document Identity != File Identity)."
                )
        if self.version < 1:
            raise ContractValidationError("version must be >= 1.")
        if self.parent_version is not None and self.parent_version >= self.version:
            raise ContractValidationError("parent_version must be strictly less than version.")


class DuplicateRelationship:
    """Enumerates how two source artifacts with equal content_fingerprint relate."""

    DUPLICATE_CANDIDATE = "duplicate_candidate"  # requires explicit MIZAN decision
    CONFIRMED_SAME_DOCUMENT = "confirmed_same_document"  # explicit decision made
    CONFIRMED_DISTINCT = "confirmed_distinct"  # explicit decision made


def classify_duplicate_candidate(
    artifact_a: SourceArtifactIdentity, artifact_b: SourceArtifactIdentity
) -> str:
    """Compare two source artifacts' content fingerprints.

    This function NEVER merges two artifacts into one document and NEVER
    deletes either one. Equal fingerprints only ever yield
    `DUPLICATE_CANDIDATE` -- promotion to `CONFIRMED_SAME_DOCUMENT` requires
    a separate, explicit MIZAN decision this function does not make (AC-06).
    Different fingerprints are reported as distinct with no further action.
    """
    if artifact_a.source_artifact_id == artifact_b.source_artifact_id:
        raise ContractValidationError("Cannot compare a source artifact against itself.")
    if artifact_a.content_fingerprint == artifact_b.content_fingerprint:
        return DuplicateRelationship.DUPLICATE_CANDIDATE
    return DuplicateRelationship.CONFIRMED_DISTINCT
