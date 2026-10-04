"""AC-01: The four core contracts are real, loadable, testable implementations
-- not README placeholders.

Evidence: all four submodules import successfully and expose a
CONTRACT_VERSION constant plus at least one concrete, instantiable class/
function with real validation behavior (proven by other AC-xx tests in this
directory actually exercising them).
"""
from mizan_contracts import canonical_v1, provenance_v1, identity_v1, stable_locator_v1


def test_all_four_contract_modules_import_and_declare_version():
    for module in (canonical_v1, provenance_v1, identity_v1, stable_locator_v1):
        assert module.CONTRACT_VERSION == "v1", (
            f"{module.__name__} must declare CONTRACT_VERSION == 'v1'."
        )


def test_canonical_contract_has_required_entities():
    required = (
        "SourceArtifact",
        "Document",
        "DocumentVersion",
        "Page",
        "Block",
        "Span",
        "Section",
        "Table",
        "TableCell",
        "RawObservation",
    )
    for name in required:
        assert hasattr(canonical_v1, name), f"canonical_v1 is missing required entity {name!r}."


def test_provenance_contract_has_a_real_validating_record_type():
    # A missing required field must be rejected (TypeError from the
    # dataclass itself), proving this is a real, enforced schema and not a
    # free-form dict-shaped placeholder.
    import pytest

    with pytest.raises(TypeError):
        provenance_v1.ProvenanceRecord()  # type: ignore[call-arg]


def test_identity_contract_has_a_real_validating_sha256_function():
    import pytest
    from mizan_contracts.errors import ContractValidationError

    with pytest.raises(ContractValidationError):
        identity_v1.validate_sha256("not-a-sha256")


def test_stable_locator_contract_has_a_real_builder_and_validator():
    locator = stable_locator_v1.build_document_locator(1)
    assert locator == "MIZAN-DOC-000001"
    stable_locator_v1.validate_locator_component(locator, "document")
