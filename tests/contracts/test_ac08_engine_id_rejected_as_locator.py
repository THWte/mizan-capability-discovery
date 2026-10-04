"""AC-08: An external engine ID can never become, or be embedded into, a
MIZAN Stable Locator.
"""
import pytest

from mizan_contracts import stable_locator_v1
from mizan_contracts.errors import ContractValidationError

_ENGINE_IDS = (
    "docling_id_12345",
    "mineru-internal-ref-99",
    "qdrant:point:7f3a",
    "pgvector_row_42",
    "database_row_id_1001",
    "row-55",
)


@pytest.mark.parametrize("engine_id", _ENGINE_IDS)
def test_engine_id_is_detected_as_external(engine_id):
    assert stable_locator_v1.is_external_engine_identifier(engine_id) is True


@pytest.mark.parametrize("engine_id", _ENGINE_IDS)
def test_engine_id_used_as_document_locator_is_rejected(engine_id):
    with pytest.raises(ContractValidationError):
        stable_locator_v1.validate_locator_component(engine_id, "document")


@pytest.mark.parametrize("engine_id", _ENGINE_IDS)
def test_engine_id_embedded_inside_an_otherwise_valid_locator_is_rejected(engine_id):
    # Even if someone tries to smuggle an engine ID into a path that
    # otherwise looks MIZAN-shaped, validation must still reject it.
    smuggled = f"MIZAN-DOC-000001/PAGE-000001/BLOCK-000001/SPAN-{engine_id}"
    with pytest.raises(ContractValidationError):
        stable_locator_v1.validate_locator_component(smuggled, "span")


def test_a_genuine_mizan_locator_is_not_flagged_as_external():
    locator = stable_locator_v1.build_document_locator(1)
    assert stable_locator_v1.is_external_engine_identifier(locator) is False
