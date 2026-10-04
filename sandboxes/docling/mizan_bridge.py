"""
MIZAN <-> Docling Contract Bridge (Sandbox Prototype)

Purpose
-------
`adapter.py` isolates Docling's own API behind `DoclingAdapter`/
`NormalizedDocumentResult`. This module is the ONE place where that
Docling-shaped output is translated into MIZAN's real, versioned core
contracts (`contracts/mizan_contracts/`): Canonical v1, Provenance v1,
Identity v1, and Stable Locator v1.

Direction of dependency (GATE 10 / Invariant 1 / Invariant 10):

    MIZAN CONTRACT
            ^
         ADAPTER   (this module)
            ^
         DOCLING

This module imports FROM `mizan_contracts` and FROM `adapter`. Nothing in
`contracts/mizan_contracts/` imports or knows about this module, `adapter.py`,
or Docling. If Docling is replaced or abandoned, only this file and
`adapter.py` need to change -- the core contracts are untouched.

What this module does NOT do
-----------------------------
It never constructs a Fact, CandidateFact, VerifiedFact, or AcceptedFact --
those types do not exist anywhere in `contracts/mizan_contracts/` by
construction (Invariant 2 / AC-10), and this bridge has no API surface that
could promote a `RawObservation` beyond Observation. Everything produced
here is Observation-stage only:

    SOURCE -> RAW EXTRACTION -> NORMALIZATION -> INTERPRETATION -> VERIFICATION -> ACCEPTED FACT
              \\_____________________________/
                      this bridge's scope (same as adapter.py)

Identity design
----------------
- `sha256` (Identity Contract) = hash of the source file's exact bytes,
  computed by `adapter.py` BEFORE conversion (so it exists even if Docling
  conversion later fails). This is byte/artifact identity.
- `content_fingerprint` (Identity Contract) = hash of the NORMALIZED TEXT,
  deliberately decoupled from file bytes. Two different source artifacts
  (e.g. a scanned PDF and a re-typed DOCX of the same contract) can share a
  `content_fingerprint` and be flagged as a *duplicate candidate*
  (`identity_v1.classify_duplicate_candidate`) without ever being treated as
  the same source artifact, and without ever being silently auto-merged
  into the same `document_id` (Invariant 5 / AC-06).
- `document_id` is never derived from either hash. Callers choose it
  explicitly (e.g. to attach a new `DocumentVersion`/source artifact to an
  existing logical document) or a fresh one is minted per ingestion.

Locator design (GATE 4 / GATE 10 / Invariant 3)
-------------------------------------------------
`LocatorAllocator` issues every Stable Locator from its own MIZAN-internal,
monotonically increasing counters. It never reads a Docling item index,
internal ID, or database row id. Every locator it produces is additionally
passed through `stable_locator_v1.validate_locator_component` before use
(defense in depth -- even a future bug in the allocator cannot smuggle an
engine-native ID into a RawObservation's `stable_locator`).
"""
from __future__ import annotations

import dataclasses
import hashlib
import pathlib
import sys
import uuid
from datetime import datetime, timezone
from typing import Optional

# Make contracts/mizan_contracts importable without packaging, the same way
# the repo-root conftest.py does for tests/contracts and tests/architecture.
# The contracts package itself has zero third-party dependencies (see
# canonical_v1.py's module docstring / Invariant 1), so this import never
# pulls in Docling, torch, or any other heavy dependency.
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_CONTRACTS_DIR = str(_REPO_ROOT / "contracts")
if _CONTRACTS_DIR not in sys.path:
    sys.path.insert(0, _CONTRACTS_DIR)

from mizan_contracts import canonical_v1, identity_v1, provenance_v1, stable_locator_v1  # noqa: E402
from mizan_contracts.errors import ContractValidationError  # noqa: E402

from adapter import NormalizedDocumentResult  # noqa: E402


class BridgeError(Exception):
    """Raised when a Docling result cannot be safely bridged into MIZAN's
    canonical contracts. Distinct from ContractValidationError: a
    BridgeError means "there is nothing valid to bridge" (e.g. the
    extraction itself failed); ContractValidationError means "what we tried
    to bridge violates a MIZAN contract" (e.g. a bad SHA-256, a malformed
    locator, or a raw/normalized text mismatch)."""


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class LocatorAllocator:
    """MIZAN-owned, purely in-memory sequence allocator for Stable Locators.

    This allocator NEVER reads a Docling-internal ID, database row id, or any
    other engine-native identifier (Invariant 3 / AC-07 / AC-08): every
    sequence number it issues comes from its own monotonically increasing
    counters, seeded at 1, regardless of what engine produced the content
    being located.
    """

    def __init__(self) -> None:
        self._page_seq = 0
        self._block_seq = 0
        self._span_seq = 0

    def next_page(self, document_locator: str) -> str:
        self._page_seq += 1
        return stable_locator_v1.build_page_locator(document_locator, self._page_seq)

    def next_block(self, page_locator: str) -> str:
        self._block_seq += 1
        return stable_locator_v1.build_block_locator(page_locator, self._block_seq)

    def next_span(self, block_locator: str) -> str:
        self._span_seq += 1
        return stable_locator_v1.build_span_locator(block_locator, self._span_seq)


@dataclasses.dataclass
class BridgeOutput:
    """Everything a caller needs to inspect the MIZAN-contract view of one
    Docling extraction. Nothing in here is a Fact or Accepted Fact -- every
    entity is Observation-stage only (Invariant 2), matching canonical_v1
    and provenance_v1 exactly. MIZAN components should depend on these
    types, never on `NormalizedDocumentResult`/`SectionResult`/
    `TableResult` directly (GATE 10)."""

    source_artifact_identity: identity_v1.SourceArtifactIdentity
    source_artifact: canonical_v1.SourceArtifact
    source_artifact_record: provenance_v1.SourceArtifactRecord
    document: canonical_v1.Document
    document_version: canonical_v1.DocumentVersion
    document_locator: str
    pages: list[canonical_v1.Page]
    blocks: list[canonical_v1.Block]
    sections: list[canonical_v1.Section]
    tables: list[canonical_v1.Table]
    raw_observations: list[canonical_v1.RawObservation]
    provenance_records: list[provenance_v1.ProvenanceRecord]
    warnings: list[str]


def bridge_to_mizan(
    result: NormalizedDocumentResult,
    *,
    document_id: Optional[str] = None,
    source_artifact_id: Optional[str] = None,
    document_version: int = 1,
    ingestion_timestamp: Optional[str] = None,
    extraction_timestamp: Optional[str] = None,
) -> BridgeOutput:
    """Translate one `DoclingAdapter.convert()` result into MIZAN's
    canonical, provenance, identity, and stable-locator contract objects.

    Raises `BridgeError` if `result.success` is False: a failed/corrupted
    extraction has no content to bridge, and a failure must never be
    silently converted into an empty-but-successful-looking Observation
    (GATE 5 / Invariant 2).

    Raises `ContractValidationError` (propagated from
    `contracts/mizan_contracts`) if anything in `result` would violate a
    MIZAN contract once bridged: a missing/invalid SHA-256, a
    normalized_text that is not genuinely NFKC(raw_text), missing
    provenance metadata, or (defensively) an engine-native identifier that
    somehow reached a locator field.
    """
    if not result.success:
        raise BridgeError(
            "Cannot bridge a failed extraction result into MIZAN contracts: "
            f"errors={result.errors!r}"
        )

    ingestion_timestamp = ingestion_timestamp or utc_now_iso()
    extraction_timestamp = extraction_timestamp or ingestion_timestamp
    source_artifact_id = source_artifact_id or f"sa-{uuid.uuid4()}"
    document_id = document_id or f"doc-{uuid.uuid4()}"

    # GATE 2 / AC-04: absence of a valid SHA-256 for the used Source
    # Artifact is a hard FAIL here, not a warning. `adapter.py` computes this
    # from the file's bytes before conversion; we still validate it
    # ourselves rather than trusting the adapter blindly.
    file_sha256 = identity_v1.validate_sha256(result.provenance.source_sha256)

    # Content fingerprint is derived from NORMALIZED TEXT, not file bytes --
    # deliberately decoupled from `sha256` so two different byte artifacts
    # representing the same logical content can be flagged as duplicate
    # *candidates* without ever being the same source artifact identity
    # (Invariant 5 / AC-06), and without ever being auto-merged.
    content_fingerprint = sha256_hex(result.normalized_text.encode("utf-8"))

    source_artifact_identity = identity_v1.SourceArtifactIdentity(
        source_artifact_id=source_artifact_id,
        sha256=file_sha256,
        content_fingerprint=content_fingerprint,
        byte_size=result.provenance.source_size_bytes,
        ingestion_timestamp=ingestion_timestamp,
    )
    source_artifact = canonical_v1.SourceArtifact(source_artifact_id=source_artifact_id)
    source_artifact_record = provenance_v1.SourceArtifactRecord(
        source_artifact_id=source_artifact_id, sha256=file_sha256
    )

    document = canonical_v1.Document(document_id=document_id)
    document_version_id = f"{document_id}-v{document_version}"
    doc_version = canonical_v1.DocumentVersion(
        document_version_id=document_version_id,
        document_id=document_id,
        version=document_version,
    )

    allocator = LocatorAllocator()
    doc_locator = stable_locator_v1.build_document_locator(1)
    # The sandbox's adapter does not yet distinguish multiple Docling pages
    # into separate MIZAN Page entities (SectionResult.page_number is
    # currently informational metadata only, not yet used to split pages
    # here) -- all content for one document version is attached to a single
    # MIZAN page. This is a documented, honest simplification, not a hidden
    # one: see sandboxes/docling/COMPARISON_AND_DECISION.md.
    page_locator = allocator.next_page(doc_locator)
    page = canonical_v1.Page(
        page_locator=page_locator, document_version_id=document_version_id, page_number=1
    )

    blocks: list[canonical_v1.Block] = []
    sections: list[canonical_v1.Section] = []
    tables: list[canonical_v1.Table] = []
    raw_observations: list[canonical_v1.RawObservation] = []
    provenance_records: list[provenance_v1.ProvenanceRecord] = []
    produced_by = f"{result.provenance.engine}@{result.provenance.engine_version}"
    settings = {"ocr_mode": result.ocr_mode, "ocr_engine": result.ocr_engine}

    def _emit_observation(span_locator: str, raw_text: str, normalized_text: str, extraction_method: str) -> None:
        # Defense in depth: even though LocatorAllocator only ever builds
        # MIZAN-owned locators, validate explicitly before use so an
        # engine-native ID could never reach a RawObservation even if a
        # future bug changed the allocator (GATE 4 / GATE 10 / AC-08).
        stable_locator_v1.validate_locator_component(span_locator, "span")
        raw_observations.append(
            canonical_v1.RawObservation(
                stable_locator=span_locator,
                raw_text=raw_text,
                normalized_text=normalized_text,
                produced_by=produced_by,
            )
        )
        provenance_records.append(
            provenance_v1.ProvenanceRecord(
                source_artifact_id=source_artifact_id,
                source_sha256=file_sha256,
                document_id=document_id,
                document_version_id=document_version_id,
                stable_locator=span_locator,
                engine=result.provenance.engine,
                engine_version=result.provenance.engine_version,
                settings=settings,
                extraction_timestamp=extraction_timestamp,
                extraction_method=extraction_method,
            )
        )

    for order_index, section in enumerate(result.sections):
        block_locator = allocator.next_block(page_locator)
        kind = "heading" if section.level > 0 else "paragraph"
        blocks.append(
            canonical_v1.Block(
                block_locator=block_locator, page_locator=page_locator, order_index=order_index, kind=kind
            )
        )
        normalized = canonical_v1.normalize_text(section.text)
        sections.append(
            canonical_v1.Section(
                block_locator=block_locator, level=section.level, raw_text=section.text, normalized_text=normalized
            )
        )
        span_locator = allocator.next_span(block_locator)
        _emit_observation(
            span_locator,
            section.text,
            normalized,
            f"docling.export_to_markdown+section_iterate[ocr_mode={result.ocr_mode}]",
        )

    for table in result.tables:
        block_locator = allocator.next_block(page_locator)
        blocks.append(
            canonical_v1.Block(
                block_locator=block_locator, page_locator=page_locator, order_index=len(blocks), kind="table"
            )
        )
        cells: list[canonical_v1.TableCell] = []
        for row_idx, row in enumerate(table.rows):
            for col_idx, raw_cell in enumerate(row):
                normalized_cell = canonical_v1.normalize_text(raw_cell)
                cells.append(
                    canonical_v1.TableCell(
                        row=row_idx, column=col_idx, raw_text=raw_cell, normalized_text=normalized_cell
                    )
                )
                span_locator = allocator.next_span(block_locator)
                _emit_observation(
                    span_locator,
                    raw_cell,
                    normalized_cell,
                    f"docling.table.export_to_dataframe[ocr_mode={result.ocr_mode}]",
                )
        caption_raw = table.caption
        caption_normalized = canonical_v1.normalize_text(caption_raw) if caption_raw is not None else None
        tables.append(
            canonical_v1.Table(
                block_locator=block_locator,
                cells=tuple(cells),
                caption_raw_text=caption_raw,
                caption_normalized_text=caption_normalized,
            )
        )

    return BridgeOutput(
        source_artifact_identity=source_artifact_identity,
        source_artifact=source_artifact,
        source_artifact_record=source_artifact_record,
        document=document,
        document_version=doc_version,
        document_locator=doc_locator,
        pages=[page],
        blocks=blocks,
        sections=sections,
        tables=tables,
        raw_observations=raw_observations,
        provenance_records=provenance_records,
        warnings=list(result.warnings),
    )


def trace_observation_to_sha256(output: BridgeOutput, stable_locator: str) -> str:
    """Structurally prove Observation -> Span -> Block -> Page -> Source
    Artifact -> SHA-256 (GATE 6 / Invariant 7 / AC-14) for one specific
    `stable_locator` present in `output.raw_observations`.

    This proves the STRUCTURAL reverse-traceability path only. It never
    claims "Accepted Fact -> SHA-256": Candidate Fact / Verification /
    Accepted Fact layers do not exist in this sandbox or in
    `contracts/mizan_contracts/` yet.

    Raises `ContractValidationError` if the locator is not found, the
    hierarchy is inconsistent, or the provenance -> source-artifact chain
    is broken.
    """
    matching = [obs for obs in output.raw_observations if obs.stable_locator == stable_locator]
    if not matching:
        raise ContractValidationError(f"No RawObservation found with stable_locator={stable_locator!r}.")

    block_locator = stable_locator.rsplit("/", 1)[0]
    stable_locator_v1.validate_hierarchy_consistency(
        document_locator=output.document_locator,
        page_locator=output.pages[0].page_locator,
        block_locator=block_locator,
        span_locator=stable_locator,
    )

    provenance = next((p for p in output.provenance_records if p.stable_locator == stable_locator), None)
    if provenance is None:
        raise ContractValidationError(f"No ProvenanceRecord found for stable_locator={stable_locator!r}.")

    return provenance_v1.trace_to_source_sha256(provenance, output.source_artifact_record)
