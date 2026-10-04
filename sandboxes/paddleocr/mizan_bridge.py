"""
MIZAN <-> PaddleOCR Contract Bridge (Sandbox Prototype)

Purpose
-------
`adapter.py` isolates PaddleOCR's own API behind `PaddleOcrAdapter`/
`NormalizedDocumentResult`. This module is the ONE place where that
PaddleOCR-shaped output is translated into MIZAN's real, versioned core
contracts (`contracts/mizan_contracts/`): Canonical v1, Provenance v1,
Identity v1, and Stable Locator v1.

Direction of dependency (A4 STEP 3 / Invariant 1 / Invariant 10):

    MIZAN CONTRACT
            ^
         ADAPTER   (this module)
            ^
        PADDLEOCR

This module imports FROM `mizan_contracts` and FROM `adapter`. Nothing in
`contracts/mizan_contracts/` imports or knows about this module, `adapter.py`,
or PaddleOCR. If PaddleOCR is replaced or abandoned, only this file and
`adapter.py` need to change -- the core contracts are untouched. This module
also has NO dependency on `sandboxes/docling/` -- it is built independently
against the same contracts, per A4's Git Isolation instruction.

What this module does NOT do
-----------------------------
It never constructs a Fact, CandidateFact, VerifiedFact, or AcceptedFact --
those types do not exist anywhere in `contracts/mizan_contracts/` by
construction, and this bridge has no API surface that could promote a
`RawObservation` beyond Observation, even when PaddleOCR's own per-line
confidence is 1.0:

    SOURCE -> RAW EXTRACTION -> NORMALIZATION -> INTERPRETATION -> VERIFICATION -> ACCEPTED FACT
              \\_____________________________/
                      this bridge's scope (same as adapter.py)

Identity design
----------------
Same design as the Docling bridge (A4 explicitly permits reusing
engine-neutral methodology): `sha256` = file-byte hash computed in
`adapter.py` before OCR runs; `content_fingerprint` = hash of the
NORMALIZED TEXT, deliberately decoupled from file bytes so two different
source artifacts can be flagged as duplicate *candidates* without being
auto-merged into the same `document_id`.

Locator design
---------------
`LocatorAllocator` issues every Stable Locator (Document/Page/Block/Span)
from its own MIZAN-internal, monotonically increasing counters. It NEVER
reads a PaddleOCR-internal index, bounding-box hash, or any other
engine-native identifier. Every locator is additionally passed through
`stable_locator_v1.validate_locator_component` before use (defense in
depth).

Multi-page support (capability difference from the Docling bridge)
---------------------------------------------------------------------
PaddleOCR's pipeline reports a real, reliable `page_index` for every
recognized line (it rasterizes and OCRs each PDF page independently), so
unlike the current Docling bridge -- which attaches all content to a single
synthetic Page because Docling's own per-item page provenance was only
partially available -- this bridge DOES split content across one MIZAN
`Page` entity per distinct PaddleOCR `page_index`, in first-seen order.
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
# The contracts package itself has zero third-party dependencies, so this
# import never pulls in PaddleOCR, paddle, or any other heavy dependency.
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_CONTRACTS_DIR = str(_REPO_ROOT / "contracts")
if _CONTRACTS_DIR not in sys.path:
    sys.path.insert(0, _CONTRACTS_DIR)

from mizan_contracts import canonical_v1, identity_v1, provenance_v1, stable_locator_v1  # noqa: E402
from mizan_contracts.errors import ContractValidationError  # noqa: E402

from adapter import NormalizedDocumentResult  # noqa: E402


class BridgeError(Exception):
    """Raised when a PaddleOCR result cannot be safely bridged into MIZAN's
    canonical contracts. Distinct from ContractValidationError: a
    BridgeError means "there is nothing valid to bridge" (e.g. the
    extraction itself failed); ContractValidationError means "what we tried
    to bridge violates a MIZAN contract"."""


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class LocatorAllocator:
    """MIZAN-owned, purely in-memory sequence allocator for Stable Locators.

    NEVER reads a PaddleOCR-internal index, bounding-box hash, or database
    row id: every sequence number comes from its own monotonically
    increasing counters, seeded at 1.
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
    PaddleOCR extraction. Nothing in here is a Fact or Accepted Fact --
    every entity is Observation-stage only, matching canonical_v1 and
    provenance_v1 exactly. MIZAN components should depend on these types,
    never on `NormalizedDocumentResult`/`SectionResult` directly."""

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
    """Translate one `PaddleOcrAdapter.convert()` result into MIZAN's
    canonical, provenance, identity, and stable-locator contract objects.

    Raises `BridgeError` if `result.success` is False: a failed/corrupted
    extraction has no content to bridge, and a failure must never be
    silently converted into an empty-but-successful-looking Observation.

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

    # Absence of a valid SHA-256 for the used Source Artifact is a hard FAIL
    # here, not a warning. `adapter.py` computes this from the file's bytes
    # before OCR runs; we still validate it ourselves rather than trusting
    # the adapter blindly.
    file_sha256 = identity_v1.validate_sha256(result.provenance.source_sha256)

    # Content fingerprint is derived from NORMALIZED TEXT, not file bytes.
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

    # Multi-page support: one MIZAN Page per distinct PaddleOCR page_number,
    # in first-seen order (see module docstring).
    pages: list[canonical_v1.Page] = []
    page_locator_by_number: dict[Optional[int], str] = {}

    def _page_locator_for(page_number: Optional[int]) -> str:
        if page_number not in page_locator_by_number:
            loc = allocator.next_page(doc_locator)
            page_locator_by_number[page_number] = loc
            pages.append(
                canonical_v1.Page(
                    page_locator=loc,
                    document_version_id=document_version_id,
                    page_number=page_number if page_number is not None else len(pages) + 1,
                )
            )
        return page_locator_by_number[page_number]

    blocks: list[canonical_v1.Block] = []
    sections: list[canonical_v1.Section] = []
    tables: list[canonical_v1.Table] = []  # always empty -- see adapter.py "Table structure"
    raw_observations: list[canonical_v1.RawObservation] = []
    provenance_records: list[provenance_v1.ProvenanceRecord] = []
    produced_by = f"{result.provenance.engine}@{result.provenance.engine_version}"
    base_settings = {
        "ocr_mode": result.ocr_mode,
        "ocr_engine": result.ocr_engine,
        "ocr_applied": result.ocr_applied,
        "model": result.provenance.model,
        "model_version": result.provenance.model_version,  # None when not available -- never fabricated
    }

    def _emit_observation(span_locator: str, raw_text: str, normalized_text: str, extraction_method: str, confidence: Optional[float]) -> None:
        # Defense in depth: validate explicitly before use so an
        # engine-native ID could never reach a RawObservation even if a
        # future bug changed the allocator.
        stable_locator_v1.validate_locator_component(span_locator, "span")
        raw_observations.append(
            canonical_v1.RawObservation(
                stable_locator=span_locator,
                raw_text=raw_text,
                normalized_text=normalized_text,
                produced_by=produced_by,
            )
        )
        settings = dict(base_settings)
        settings["engine_confidence"] = confidence  # engine confidence, NOT a MIZAN verification signal
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
        page_locator = _page_locator_for(section.page_number)
        block_locator = allocator.next_block(page_locator)
        # PaddleOCR's plain OCR pipeline has no heading/layout classification
        # capability (SectionResult.level is always 0 -- see adapter.py), so
        # every block is honestly reported as "paragraph", never "heading".
        blocks.append(
            canonical_v1.Block(
                block_locator=block_locator, page_locator=page_locator, order_index=order_index, kind="paragraph"
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
            f"paddleocr.predict.rec_texts[ocr_mode={result.ocr_mode}]",
            section.confidence,
        )

    if not pages:
        # Degenerate case: a "successful" result with zero recognized lines
        # (e.g. a genuinely blank page) still needs at least one Page entity
        # for the document version to be structurally valid.
        pages.append(
            canonical_v1.Page(
                page_locator=allocator.next_page(doc_locator),
                document_version_id=document_version_id,
                page_number=1,
            )
        )

    return BridgeOutput(
        source_artifact_identity=source_artifact_identity,
        source_artifact=source_artifact,
        source_artifact_record=source_artifact_record,
        document=document,
        document_version=doc_version,
        document_locator=doc_locator,
        pages=pages,
        blocks=blocks,
        sections=sections,
        tables=tables,
        raw_observations=raw_observations,
        provenance_records=provenance_records,
        warnings=list(result.warnings),
    )


def trace_observation_to_sha256(output: BridgeOutput, stable_locator: str) -> str:
    """Structurally prove Observation -> Span -> Block -> Page -> Source
    Artifact -> SHA-256 for one specific `stable_locator` present in
    `output.raw_observations`.

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
    page_locator = block_locator.rsplit("/", 1)[0]
    page = next((p for p in output.pages if p.page_locator == page_locator), None)
    if page is None:
        raise ContractValidationError(f"No Page found owning block_locator={block_locator!r}.")

    stable_locator_v1.validate_hierarchy_consistency(
        document_locator=output.document_locator,
        page_locator=page.page_locator,
        block_locator=block_locator,
        span_locator=stable_locator,
    )

    provenance = next((p for p in output.provenance_records if p.stable_locator == stable_locator), None)
    if provenance is None:
        raise ContractValidationError(f"No ProvenanceRecord found for stable_locator={stable_locator!r}.")

    return provenance_v1.trace_to_source_sha256(provenance, output.source_artifact_record)
