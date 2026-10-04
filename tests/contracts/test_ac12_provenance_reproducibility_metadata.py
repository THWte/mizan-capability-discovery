"""AC-12: Provenance records reproducibility metadata; it is never allowed
to go missing from a machine-produced observation's provenance record.
"""
import dataclasses

import pytest

from mizan_contracts import provenance_v1
from mizan_contracts.errors import ContractValidationError

_SHA256 = "1" * 64
_SPAN_LOCATOR = "MIZAN-DOC-000001/PAGE-000001/BLOCK-000001/SPAN-000001"

_REQUIRED_FIELDS = (
    "engine",
    "engine_version",
    "settings",
    "extraction_timestamp",
    "extraction_method",
    "source_sha256",
)


def _base_kwargs(**overrides):
    kwargs = dict(
        source_artifact_id="A1",
        source_sha256=_SHA256,
        document_id="D1",
        document_version_id="D1-v1",
        stable_locator=_SPAN_LOCATOR,
        engine="test-engine",
        engine_version="1.0.0",
        settings={"ocr": False},
        extraction_timestamp="2026-01-01T00:00:00Z",
        extraction_method="direct-text-layer",
    )
    kwargs.update(overrides)
    return kwargs


def test_full_provenance_record_declares_every_reproducibility_field():
    record = provenance_v1.ProvenanceRecord(**_base_kwargs())
    for field_name in _REQUIRED_FIELDS:
        assert getattr(record, field_name), f"{field_name} must be populated."


@pytest.mark.parametrize("missing_field", _REQUIRED_FIELDS)
def test_missing_reproducibility_field_is_rejected(missing_field):
    kwargs = _base_kwargs()
    kwargs[missing_field] = "" if missing_field != "settings" else kwargs[missing_field]
    if missing_field == "settings":
        # settings has a different invalid form: non-dict.
        with pytest.raises(ContractValidationError):
            provenance_v1.ProvenanceRecord(**{**kwargs, "settings": "not-a-dict"})
        return
    with pytest.raises(ContractValidationError):
        provenance_v1.ProvenanceRecord(**kwargs)


def test_model_and_model_version_are_optional_for_non_model_extraction():
    # A rule-based, non-ML extraction method (e.g. a text-layer PDF read) may
    # legitimately omit model/model_version -- this is documented semantics,
    # not a silent gap, and is distinct from omitting engine/engine_version.
    record = provenance_v1.ProvenanceRecord(**_base_kwargs())
    assert record.model is None
    assert record.model_version is None


def test_confidence_out_of_range_is_rejected():
    with pytest.raises(ContractValidationError):
        provenance_v1.ProvenanceRecord(**_base_kwargs(confidence=1.5))
    with pytest.raises(ContractValidationError):
        provenance_v1.ProvenanceRecord(**_base_kwargs(confidence=-0.1))


def test_provenance_record_declares_contract_version():
    record = provenance_v1.ProvenanceRecord(**_base_kwargs())
    assert record.contract_version == "v1"
