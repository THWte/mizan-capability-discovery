"""MIZAN Evidence Resolution Contract v1.

Resolves relationships among RawObservations. It never creates Fact,
VerifiedFact, or AcceptedFact. Truth-status belongs to later verification.
"""
from __future__ import annotations

import dataclasses
import hashlib
from enum import Enum
from typing import Iterable

from mizan_contracts.canonical_v1 import RawObservation


class EvidenceResolutionError(ValueError):
    pass


class EvidenceState(str, Enum):
    OBSERVED = "OBSERVED"
    CORROBORATED = "CORROBORATED"
    CONFLICTED = "CONFLICTED"
    UNRESOLVED = "UNRESOLVED"
    REJECTED = "REJECTED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


@dataclasses.dataclass(frozen=True, kw_only=True)
class ObservationRef:
    observation_id: str
    stable_locator: str
    produced_by: str
    normalized_text: str

    @classmethod
    def from_raw(cls, observation_id: str, observation: RawObservation) -> "ObservationRef":
        if not observation_id:
            raise EvidenceResolutionError("observation_id is required")
        return cls(
            observation_id=observation_id,
            stable_locator=observation.stable_locator,
            produced_by=observation.produced_by,
            normalized_text=observation.normalized_text,
        )


@dataclasses.dataclass(frozen=True, kw_only=True)
class EvidenceResolutionRecord:
    resolution_id: str
    state: EvidenceState
    observations: tuple[ObservationRef, ...]
    reason_codes: tuple[str, ...]
    requires_human_review: bool

    def __post_init__(self) -> None:
        if not self.resolution_id:
            raise EvidenceResolutionError("resolution_id is required")
        if not self.observations:
            raise EvidenceResolutionError("at least one observation is required")
        if self.state in (EvidenceState.CONFLICTED, EvidenceState.UNRESOLVED, EvidenceState.REVIEW_REQUIRED) and not self.requires_human_review:
            raise EvidenceResolutionError("uncertain/conflicted resolution must require human review")


def _resolution_id(refs: tuple[ObservationRef, ...]) -> str:
    material = "|".join(sorted(r.observation_id for r in refs)).encode("utf-8")
    return "ER-" + hashlib.sha256(material).hexdigest()[:24]


def resolve_observations(
    observations: Iterable[tuple[str, RawObservation]],
    *,
    force_review: bool = False,
) -> EvidenceResolutionRecord:
    refs = tuple(ObservationRef.from_raw(i, o) for i, o in observations)
    if not refs:
        raise EvidenceResolutionError("cannot resolve an empty observation set")
    if len({r.observation_id for r in refs}) != len(refs):
        raise EvidenceResolutionError("duplicate observation_id is forbidden")

    rid = _resolution_id(refs)
    if force_review:
        return EvidenceResolutionRecord(
            resolution_id=rid,
            state=EvidenceState.REVIEW_REQUIRED,
            observations=refs,
            reason_codes=("POLICY_REQUIRES_REVIEW",),
            requires_human_review=True,
        )

    if len(refs) == 1:
        return EvidenceResolutionRecord(
            resolution_id=rid,
            state=EvidenceState.OBSERVED,
            observations=refs,
            reason_codes=("SINGLE_OBSERVATION_ONLY",),
            requires_human_review=False,
        )

    locators = {r.stable_locator for r in refs}
    if len(locators) > 1:
        return EvidenceResolutionRecord(
            resolution_id=rid,
            state=EvidenceState.REVIEW_REQUIRED,
            observations=refs,
            reason_codes=("STABLE_LOCATOR_MISMATCH",),
            requires_human_review=True,
        )

    values = {r.normalized_text for r in refs}
    producers = {r.produced_by for r in refs}
    if len(values) == 1 and len(producers) >= 2:
        return EvidenceResolutionRecord(
            resolution_id=rid,
            state=EvidenceState.CORROBORATED,
            observations=refs,
            reason_codes=("INDEPENDENT_PRODUCERS_SAME_NORMALIZED_TEXT",),
            requires_human_review=False,
        )
    if len(values) == 1:
        return EvidenceResolutionRecord(
            resolution_id=rid,
            state=EvidenceState.OBSERVED,
            observations=refs,
            reason_codes=("REPEATED_SAME_PRODUCER_NOT_CORROBORATION",),
            requires_human_review=False,
        )

    return EvidenceResolutionRecord(
        resolution_id=rid,
        state=EvidenceState.CONFLICTED,
        observations=refs,
        reason_codes=("OBSERVATION_TEXT_DISAGREEMENT",),
        requires_human_review=True,
    )


def unresolved(
    observations: Iterable[tuple[str, RawObservation]],
    *,
    reason_code: str,
) -> EvidenceResolutionRecord:
    refs = tuple(ObservationRef.from_raw(i, o) for i, o in observations)
    if not refs:
        raise EvidenceResolutionError("cannot create unresolved record without observations")
    if not reason_code:
        raise EvidenceResolutionError("reason_code is required")
    return EvidenceResolutionRecord(
        resolution_id=_resolution_id(refs),
        state=EvidenceState.UNRESOLVED,
        observations=refs,
        reason_codes=(reason_code,),
        requires_human_review=True,
    )


def reject(
    observation_id: str,
    observation: RawObservation,
    *,
    reason_code: str,
) -> EvidenceResolutionRecord:
    if not reason_code:
        raise EvidenceResolutionError("reason_code is required")
    ref = ObservationRef.from_raw(observation_id, observation)
    return EvidenceResolutionRecord(
        resolution_id=_resolution_id((ref,)),
        state=EvidenceState.REJECTED,
        observations=(ref,),
        reason_codes=(reason_code,),
        requires_human_review=False,
    )
