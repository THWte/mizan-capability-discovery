"""
MIZAN Canonical Contract v1

Implements docs/architecture/ARCHITECTURAL_INVARIANTS.md Invariant 1
(MIZAN Contract Before Engine) and Invariant 2 (Observation != Evidence !=
Fact != Accepted Fact).

This module defines the MIZAN-owned shape every engine adapter must
translate its native output into: Source Artifact, Document, Document
Version, Page, Block, Span, Section, Table, Table Cell, and Raw
Observation.

Hard rule (Invariant 2): this module defines ONLY Observation-stage
entities. It intentionally contains no "Fact", "CandidateFact", or
"AcceptedFact" class, field, or method anywhere -- promoting a
RawObservation to a Fact or Accepted Fact is not an operation this contract
exposes, by construction, not by convention (AC-10). Those stages belong to
MIZAN's interpretation/verification layers, which do not exist in this
repository yet (see ADR-0001).

Hard rule (Invariant 1 / Invariant 10): this module and every other module
in `contracts/mizan_contracts/` MUST NOT import, reference, or depend on
any third-party document-intelligence or retrieval engine (Docling,
PaddleOCR, MinerU, Qdrant, pgvector, or any other). Engines adapt to this
contract via their own adapters (e.g. `sandboxes/docling/adapter.py`); this
contract never imports or adapts to them. AC-02 verifies this by repository
scan.

raw_text vs normalized_text
---------------------------
Every entity in this module that carries extracted text keeps `raw_text`
(exactly what the producing engine emitted) and `normalized_text` (that
text after MIZAN's Unicode NFKC normalization step) as two separate,
independently-readable fields. Neither ever silently overwrites the other.
"""
from __future__ import annotations

import dataclasses
import unicodedata
from typing import Optional

from .errors import ContractValidationError

CONTRACT_VERSION = "v1"


def normalize_text(raw_text: str) -> str:
    """The one, shared MIZAN-mandated normalization function: Unicode NFKC.
    Every canonical entity that stores `normalized_text` must derive it via
    this function (or an equal one), never via engine-specific logic.
    """
    return unicodedata.normalize("NFKC", raw_text)


def _require_text_pair(raw_text: str, normalized_text: str) -> None:
    if raw_text is None or normalized_text is None:
        raise ContractValidationError("raw_text and normalized_text are both required (may be '').")


@dataclasses.dataclass(frozen=True, kw_only=True)
class SourceArtifact:
    """Canonical reference to a source artifact. Identity/SHA-256 rules for
    this entity are owned by `identity_v1.SourceArtifactIdentity` -- this
    class only carries the reference used to link canonical entities to it,
    keeping the two contracts independently usable.
    """

    contract_version: str = dataclasses.field(default=CONTRACT_VERSION, init=False)
    source_artifact_id: str

    def __post_init__(self) -> None:
        if not self.source_artifact_id:
            raise ContractValidationError("source_artifact_id is required.")


@dataclasses.dataclass(frozen=True, kw_only=True)
class Document:
    """Canonical reference to a logical document. Identity rules for this
    entity are owned by `identity_v1.DocumentIdentity`.
    """

    contract_version: str = dataclasses.field(default=CONTRACT_VERSION, init=False)
    document_id: str

    def __post_init__(self) -> None:
        if not self.document_id:
            raise ContractValidationError("document_id is required.")


@dataclasses.dataclass(frozen=True, kw_only=True)
class DocumentVersion:
    contract_version: str = dataclasses.field(default=CONTRACT_VERSION, init=False)
    document_version_id: str
    document_id: str
    version: int

    def __post_init__(self) -> None:
        if not self.document_version_id or not self.document_id:
            raise ContractValidationError("document_version_id and document_id are required.")
        if self.version < 1:
            raise ContractValidationError("version must be >= 1.")


@dataclasses.dataclass(frozen=True, kw_only=True)
class Page:
    contract_version: str = dataclasses.field(default=CONTRACT_VERSION, init=False)
    page_locator: str
    document_version_id: str
    page_number: int

    def __post_init__(self) -> None:
        if self.page_number < 1:
            raise ContractValidationError("page_number must be >= 1.")


@dataclasses.dataclass(frozen=True, kw_only=True)
class Block:
    """A heading/paragraph/table unit, preserving document order via
    `order_index` (Invariant: content order must be preserved, see
    sandboxes/docling/adapter.py SectionResult for the sandbox-local
    precedent this generalizes)."""

    contract_version: str = dataclasses.field(default=CONTRACT_VERSION, init=False)
    block_locator: str
    page_locator: str
    order_index: int
    kind: str  # "paragraph" | "heading" | "table"

    def __post_init__(self) -> None:
        if self.order_index < 0:
            raise ContractValidationError("order_index must be >= 0.")
        if self.kind not in ("paragraph", "heading", "table"):
            raise ContractValidationError(f"Unknown block kind: {self.kind!r}.")


@dataclasses.dataclass(frozen=True, kw_only=True)
class Span:
    contract_version: str = dataclasses.field(default=CONTRACT_VERSION, init=False)
    span_locator: str
    block_locator: str
    start_offset: int
    end_offset: int

    def __post_init__(self) -> None:
        if self.start_offset < 0 or self.end_offset < self.start_offset:
            raise ContractValidationError("Invalid span offsets.")


@dataclasses.dataclass(frozen=True, kw_only=True)
class Section:
    """A heading/paragraph text unit. Raw extraction + normalization only --
    never an interpretation of what the text means."""

    contract_version: str = dataclasses.field(default=CONTRACT_VERSION, init=False)
    block_locator: str
    level: int  # 0 = body paragraph, 1+ = heading level
    raw_text: str
    normalized_text: str

    def __post_init__(self) -> None:
        _require_text_pair(self.raw_text, self.normalized_text)
        if self.level < 0:
            raise ContractValidationError("level must be >= 0.")


@dataclasses.dataclass(frozen=True, kw_only=True)
class TableCell:
    contract_version: str = dataclasses.field(default=CONTRACT_VERSION, init=False)
    row: int
    column: int
    raw_text: str
    normalized_text: str

    def __post_init__(self) -> None:
        _require_text_pair(self.raw_text, self.normalized_text)
        if self.row < 0 or self.column < 0:
            raise ContractValidationError("row/column must be >= 0.")


@dataclasses.dataclass(frozen=True, kw_only=True)
class Table:
    contract_version: str = dataclasses.field(default=CONTRACT_VERSION, init=False)
    block_locator: str
    cells: tuple[TableCell, ...]
    caption_raw_text: Optional[str] = None
    caption_normalized_text: Optional[str] = None

    def __post_init__(self) -> None:
        if not isinstance(self.cells, tuple):
            raise ContractValidationError("cells must be a tuple of TableCell.")


@dataclasses.dataclass(frozen=True, kw_only=True)
class RawObservation:
    """The canonical Observation entity (Invariant 2).

    This class defines no `status`, `to_fact()`, `to_accepted_fact()`, or
    any field/method that could promote it beyond Observation. That
    promotion is intentionally impossible through this contract's API
    surface (AC-10) -- it requires MIZAN's interpretation/verification
    layers, which are out of scope for this change (see ADR-0001).
    """

    contract_version: str = dataclasses.field(default=CONTRACT_VERSION, init=False)
    stable_locator: str  # a span_locator: where this observation was found
    raw_text: str
    normalized_text: str
    produced_by: str  # informational free-text engine name, NOT an identity

    def __post_init__(self) -> None:
        _require_text_pair(self.raw_text, self.normalized_text)
        if not self.stable_locator:
            raise ContractValidationError("stable_locator is required.")
        if not self.produced_by:
            raise ContractValidationError("produced_by is required.")
