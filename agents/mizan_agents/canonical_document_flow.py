"""MIZAN Canonical Document Flow v1.

Binds source identity, document identity, routing, canonical observations,
provenance, and evidence resolution into one deterministic end-to-end
contract. It does not execute external engines and cannot create facts.
"""
from __future__ import annotations

import dataclasses
from typing import Iterable

from mizan_contracts.canonical_v1 import RawObservation
from mizan_contracts.identity_v1 import DocumentIdentity, SourceArtifactIdentity
from mizan_contracts.provenance_v1 import ProvenanceRecord, SourceArtifactRecord, trace_to_source_sha256

from .document_routing import DocumentProfile, Provider, RouteDecision, RoutingStatus, route_document
from .evidence_resolution import EvidenceResolutionRecord, resolve_observations


class CanonicalFlowError(ValueError):
    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class ObservationEnvelope:
    observation_id: str
    observation: RawObservation
    provenance: ProvenanceRecord

    def __post_init__(self) -> None:
        if not self.observation_id:
            raise CanonicalFlowError("observation_id is required")
        if self.observation.stable_locator != self.provenance.stable_locator:
            raise CanonicalFlowError("observation/provenance stable_locator mismatch")
        if self.observation.produced_by != self.provenance.engine:
            raise CanonicalFlowError("observation producer must match provenance engine")


@dataclasses.dataclass(frozen=True, kw_only=True)
class CanonicalDocumentFlowResult:
    source_artifact_id: str
    source_sha256: str
    document_id: str
    route: RouteDecision
    evidence_resolution: EvidenceResolutionRecord
    observation_ids: tuple[str, ...]
    requires_human_review: bool
    production_approved: bool = False

    def __post_init__(self) -> None:
        if self.production_approved:
            raise CanonicalFlowError("A7 flow cannot production-approve providers or facts")


def _allowed_providers(route: RouteDecision) -> set[str]:
    values = set()
    if route.primary is not Provider.NONE:
        values.add(route.primary.value)
    if route.secondary is not Provider.NONE:
        values.add(route.secondary.value)
    return values


def run_canonical_document_flow(
    *,
    source_identity: SourceArtifactIdentity,
    document_identity: DocumentIdentity,
    source_record: SourceArtifactRecord,
    profile: DocumentProfile,
    observations: Iterable[ObservationEnvelope],
) -> CanonicalDocumentFlowResult:
    envelopes = tuple(observations)
    if not envelopes:
        raise CanonicalFlowError("at least one observation envelope is required")

    if source_identity.source_artifact_id != source_record.source_artifact_id:
        raise CanonicalFlowError("source identity/source record ID mismatch")
    if source_identity.sha256 != source_record.sha256:
        raise CanonicalFlowError("source identity/source record SHA-256 mismatch")
    if source_identity.source_artifact_id not in document_identity.source_artifact_ids:
        raise CanonicalFlowError("document identity does not reference this source artifact")

    route = route_document(profile)
    if route.status is RoutingStatus.UNSUPPORTED or route.primary is Provider.NONE:
        raise CanonicalFlowError("document profile has no executable candidate route")

    allowed = _allowed_providers(route)
    seen = set()
    pairs = []
    for envelope in envelopes:
        if envelope.observation_id in seen:
            raise CanonicalFlowError("duplicate observation_id")
        seen.add(envelope.observation_id)
        p = envelope.provenance
        if p.source_artifact_id != source_identity.source_artifact_id:
            raise CanonicalFlowError("provenance source_artifact_id mismatch")
        if p.source_sha256 != source_identity.sha256:
            raise CanonicalFlowError("provenance source SHA-256 mismatch")
        if p.document_id != document_identity.document_id:
            raise CanonicalFlowError("provenance document_id mismatch")
        trace_to_source_sha256(p, source_record)
        if p.engine not in allowed:
            raise CanonicalFlowError(f"engine {p.engine!r} is outside the MIZAN route for this document")
        pairs.append((envelope.observation_id, envelope.observation))

    resolution = resolve_observations(pairs)
    requires_review = route.status is RoutingStatus.REVIEW_REQUIRED or resolution.requires_human_review
    return CanonicalDocumentFlowResult(
        source_artifact_id=source_identity.source_artifact_id,
        source_sha256=source_identity.sha256,
        document_id=document_identity.document_id,
        route=route,
        evidence_resolution=resolution,
        observation_ids=tuple(e.observation_id for e in envelopes),
        requires_human_review=requires_review,
    )