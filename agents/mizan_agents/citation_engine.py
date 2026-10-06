"""MIZAN Citation Engine v1.

Creates durable, verifiable references to canonical observation locations.
A citation proves traceability to source bytes; it does not prove truth.
"""
from __future__ import annotations
import dataclasses
import hashlib

from mizan_contracts.canonical_v1 import Block, DocumentVersion, Page, RawObservation, Span, normalize_text
from mizan_contracts.identity_v1 import DocumentIdentity, SourceArtifactIdentity
from mizan_contracts.provenance_v1 import ProvenanceRecord, SourceArtifactRecord, trace_to_source_sha256
from mizan_contracts.stable_locator_v1 import validate_hierarchy_consistency


class CitationError(ValueError):
    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class CitationRecord:
    citation_id: str
    source_artifact_id: str
    source_sha256: str
    document_id: str
    document_version_id: str
    page_number: int
    document_locator: str
    page_locator: str
    block_locator: str
    span_locator: str
    span_offsets: tuple[int, int]
    observation_id: str
    quoted_raw_text: str
    quoted_normalized_text: str
    evidentiary_authority: bool = False
    fact_status: str | None = None

    def __post_init__(self) -> None:
        if self.evidentiary_authority:
            raise CitationError("citation cannot grant evidentiary authority")
        if self.fact_status is not None:
            raise CitationError("citation cannot carry fact status")
        if not self.citation_id or not self.observation_id:
            raise CitationError("citation_id and observation_id are required")


def _citation_id(source_sha256: str, span_locator: str, observation_id: str) -> str:
    material=f"{source_sha256}|{span_locator}|{observation_id}".encode("utf-8")
    return "CIT-" + hashlib.sha256(material).hexdigest()[:24]


def create_citation(
    *,
    observation_id: str,
    observation: RawObservation,
    provenance: ProvenanceRecord,
    source_identity: SourceArtifactIdentity,
    source_record: SourceArtifactRecord,
    document_identity: DocumentIdentity,
    document_version: DocumentVersion,
    page: Page,
    block: Block,
    span: Span,
) -> CitationRecord:
    if not observation_id:
        raise CitationError("observation_id is required")
    if observation.stable_locator != span.span_locator or provenance.stable_locator != span.span_locator:
        raise CitationError("observation/provenance must resolve to the cited span")
    if observation.produced_by != provenance.engine:
        raise CitationError("observation producer/provenance engine mismatch")
    if provenance.source_artifact_id != source_identity.source_artifact_id:
        raise CitationError("provenance/source identity mismatch")
    if source_identity.source_artifact_id != source_record.source_artifact_id:
        raise CitationError("source record/source identity mismatch")
    if source_identity.sha256 != source_record.sha256 or provenance.source_sha256 != source_identity.sha256:
        raise CitationError("citation source SHA-256 chain mismatch")
    if source_identity.source_artifact_id not in document_identity.source_artifact_ids:
        raise CitationError("document identity does not reference source artifact")
    if provenance.document_id != document_identity.document_id or document_version.document_id != document_identity.document_id:
        raise CitationError("document identity/version/provenance mismatch")
    if provenance.document_version_id != document_version.document_version_id:
        raise CitationError("document version/provenance mismatch")
    if page.document_version_id != document_version.document_version_id:
        raise CitationError("page/document version mismatch")
    if block.page_locator != page.page_locator or span.block_locator != block.block_locator:
        raise CitationError("page/block/span canonical relationship mismatch")

    parts=span.span_locator.split("/")
    document_locator="/".join(parts[:1])
    page_locator="/".join(parts[:2])
    block_locator="/".join(parts[:3])
    validate_hierarchy_consistency(document_locator, page_locator, block_locator, span.span_locator)
    if page.page_locator != page_locator or block.block_locator != block_locator:
        raise CitationError("canonical entities do not match MIZAN locator hierarchy")

    trace_to_source_sha256(provenance, source_record)

    start,end=span.start_offset,span.end_offset
    if end > len(observation.raw_text):
        raise CitationError("span offsets exceed observation raw text")
    quoted_raw=observation.raw_text[start:end]
    # normalized text is preserved from the canonical observation; no new semantic normalization is invented.
    quoted_normalized=observation.normalized_text[start:end] if end <= len(observation.normalized_text) else observation.normalized_text

    return CitationRecord(
        citation_id=_citation_id(source_identity.sha256, span.span_locator, observation_id),
        source_artifact_id=source_identity.source_artifact_id,
        source_sha256=source_identity.sha256,
        document_id=document_identity.document_id,
        document_version_id=document_version.document_version_id,
        page_number=page.page_number,
        document_locator=document_locator,
        page_locator=page_locator,
        block_locator=block_locator,
        span_locator=span.span_locator,
        span_offsets=(start,end),
        observation_id=observation_id,
        quoted_raw_text=quoted_raw,
        quoted_normalized_text=quoted_normalized,
    )


def verify_citation(citation: CitationRecord, *, source_record: SourceArtifactRecord) -> bool:
    if citation.source_artifact_id != source_record.source_artifact_id:
        return False
    if citation.source_sha256 != source_record.sha256:
        return False
    try:
        validate_hierarchy_consistency(
            citation.document_locator,
            citation.page_locator,
            citation.block_locator,
            citation.span_locator,
        )
    except Exception:
        return False
    expected=_citation_id(citation.source_sha256,citation.span_locator,citation.observation_id)
    return expected == citation.citation_id
