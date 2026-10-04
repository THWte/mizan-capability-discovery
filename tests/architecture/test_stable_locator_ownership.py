"""
Architecture validation: Stable Locator ownership.

Validates Invariant 3 (MIZAN Owns Identity and Stable Locators):
see docs/architecture/ARCHITECTURAL_INVARIANTS.md#3-mizan-owns-identity-and-stable-locators

Status update (architecture/contracts-v1): contracts/stable-locator-contract-v1/
now has a real reference implementation (contracts/mizan_contracts/stable_locator_v1.py,
also exercised directly in tests/contracts/test_ac07_*.py and
tests/contracts/test_ac08_*.py). The first assertion below is now REAL, not
a placeholder. The second assertion (engine-replacement scenario) still
requires a second real engine adapter alongside sandboxes/docling/adapter.py,
which does not exist yet, and stays SKIP.
"""
import pytest

from mizan_contracts import stable_locator_v1
from mizan_contracts.errors import ContractValidationError


def test_stable_locator_is_not_a_raw_engine_id():
    """A stable locator issued by MIZAN must be a MIZAN-generated
    identifier, never a raw pass-through of an engine's internal ID."""
    # A genuine MIZAN-built locator is accepted.
    mizan_locator = stable_locator_v1.build_document_locator(1)
    stable_locator_v1.validate_locator_component(mizan_locator, "document")

    # A raw engine-native ID (Docling DocItem ref, Qdrant point ID, a bare
    # database row ID) is rejected outright -- it can never become, or be
    # embedded into, a MIZAN stable locator.
    for engine_native_id in ("docling-docitem-ref-42", "qdrant:point:9f1", "row-7"):
        assert stable_locator_v1.is_external_engine_identifier(engine_native_id) is True
        with pytest.raises(ContractValidationError):
            stable_locator_v1.validate_locator_component(engine_native_id, "document")


@pytest.mark.skip(
    reason=(
        "Only one engine adapter exists today (sandboxes/docling/adapter.py). "
        "Proving a stable locator survives ENGINE REPLACEMENT requires a "
        "second real adapter processing the same source document so the "
        "two engine-local ID schemes can be shown to resolve to the same "
        "MIZAN document identity. No second engine adapter exists yet."
    )
)
def test_stable_locator_survives_engine_replacement():
    raise NotImplementedError(
        "Implement once at least two engine adapters exist that can "
        "process the same document, to prove locator stability across "
        "engine swaps."
    )
