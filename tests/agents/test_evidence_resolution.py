import dataclasses
import pytest

from contracts.mizan_contracts.canonical_v1 import RawObservation, normalize_text
from agents.mizan_agents.evidence_resolution import (
    EvidenceResolutionError, EvidenceState, resolve_observations, unresolved, reject
)


def obs(text, engine="engine-a", locator="MIZAN-DOC-1/PAGE-1/BLOCK-1/SPAN-1"):
    return RawObservation(
        stable_locator=locator,
        raw_text=text,
        normalized_text=normalize_text(text),
        produced_by=engine,
    )


def test_single_observation_stays_observed_not_fact():
    r = resolve_observations([("o1", obs("نص"))])
    assert r.state is EvidenceState.OBSERVED
    assert not hasattr(r, "fact")
    assert not hasattr(r, "accepted_fact")


def test_same_text_from_two_engines_is_corroborated_not_verified():
    r = resolve_observations([("o1", obs("نص", "docling")), ("o2", obs("نص", "paddleocr"))])
    assert r.state is EvidenceState.CORROBORATED
    assert r.requires_human_review is False
    assert not hasattr(r, "verified")


def test_conflicting_engine_outputs_are_preserved_and_review_required():
    r = resolve_observations([("o1", obs("المبلغ 100", "docling")), ("o2", obs("المبلغ 900", "paddleocr"))])
    assert r.state is EvidenceState.CONFLICTED
    assert r.requires_human_review is True
    assert [x.normalized_text for x in r.observations] == ["المبلغ 100", "المبلغ 900"]


def test_force_review_overrides_apparent_corroboration():
    r = resolve_observations([("o1", obs("نص")), ("o2", obs("نص", "engine-b"))], force_review=True)
    assert r.state is EvidenceState.REVIEW_REQUIRED


def test_empty_resolution_is_forbidden():
    with pytest.raises(EvidenceResolutionError):
        resolve_observations([])


def test_duplicate_observation_id_is_forbidden():
    with pytest.raises(EvidenceResolutionError):
        resolve_observations([("o1", obs("أ")), ("o1", obs("ب"))])


def test_unresolved_requires_review_and_preserves_observation():
    r = unresolved([("o1", obs("غير واضح"))], reason_code="LOW_OCR_QUALITY")
    assert r.state is EvidenceState.UNRESOLVED
    assert r.requires_human_review


def test_rejection_is_not_truth_or_fact_promotion():
    r = reject("o1", obs("garbage"), reason_code="CORRUPT_EXTRACTION")
    assert r.state is EvidenceState.REJECTED
    assert not hasattr(r, "fact")


def test_uncertain_record_cannot_disable_review():
    base = resolve_observations([("o1", obs("أ")), ("o2", obs("ب"))])
    with pytest.raises(EvidenceResolutionError):
        dataclasses.replace(base, requires_human_review=False)


def test_resolution_id_is_order_independent():
    a = ("o1", obs("أ"))
    b = ("o2", obs("أ", "b"))
    assert resolve_observations([a,b]).resolution_id == resolve_observations([b,a]).resolution_id


def test_forbidden_truth_states_do_not_exist():
    names = {x.name for x in EvidenceState}
    assert "FACT" not in names
    assert "VERIFIED_FACT" not in names
    assert "ACCEPTED_FACT" not in names
