"""AC-17: Every contract declares its version explicitly and
programmatically checkable -- not merely by folder name or README text.
"""
from mizan_contracts import canonical_v1, identity_v1, provenance_v1, stable_locator_v1

_SHA256 = "6" * 64
_SPAN_LOCATOR = "MIZAN-DOC-000001/PAGE-000001/BLOCK-000001/SPAN-000001"


def test_module_level_version_constants():
    for module in (canonical_v1, identity_v1, provenance_v1, stable_locator_v1):
        assert hasattr(module, "CONTRACT_VERSION")
        assert module.CONTRACT_VERSION == "v1"


def test_instance_level_version_field_is_present_and_correct():
    document = canonical_v1.Document(document_id="D1")
    assert document.contract_version == "v1"

    artifact = identity_v1.SourceArtifactIdentity(
        source_artifact_id="A1",
        sha256=_SHA256,
        content_fingerprint="fp",
        byte_size=1,
        ingestion_timestamp="t",
    )
    assert artifact.contract_version == "v1"

    provenance = provenance_v1.ProvenanceRecord(
        source_artifact_id="A1",
        source_sha256=_SHA256,
        document_id="D1",
        document_version_id="D1-v1",
        stable_locator=_SPAN_LOCATOR,
        engine="e",
        engine_version="1",
        settings={},
        extraction_timestamp="t",
        extraction_method="m",
    )
    assert provenance.contract_version == "v1"


def test_version_field_cannot_be_overridden_by_caller():
    # contract_version is init=False: callers cannot pass a different
    # version string and have it silently accepted -- it is always
    # computed by the module's own CONTRACT_VERSION, never caller-supplied.
    import pytest

    with pytest.raises(TypeError):
        canonical_v1.Document(document_id="D1", contract_version="v2")  # type: ignore[call-arg]
