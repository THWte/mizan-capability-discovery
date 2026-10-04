"""
Architecture validation placeholder: Stable Locator ownership.

Validates Invariant 3 (MIZAN Owns Identity and Stable Locators):
see docs/architecture/ARCHITECTURAL_INVARIANTS.md#3-mizan-owns-identity-and-stable-locators

Intended future assertions (once contracts/stable-locator-contract-v1/ has a
concrete schema and a reference implementation exists):

1. A stable locator issued by MIZAN for a given document/page/region must be
   a MIZAN-generated identifier, never a raw pass-through of an engine's
   internal ID (e.g. a Docling `DocItem` reference, a file byte offset, or a
   library-version-specific index).
2. Replacing or upgrading the underlying extraction engine must not change,
   invalidate, or require migration of any previously-issued stable locator.
3. Two different engines processing the same source document must be
   resolvable to the same MIZAN document identity via stable locators, even
   though their engine-local IDs differ completely.

This module intentionally contains no real assertions yet: there is no
stable-locator implementation to validate. Per architectural convention
(see tests/architecture/README.md), the test SKIPS with an explicit reason
rather than being deleted or fabricated as passing.
"""
import pytest


@pytest.mark.skip(
    reason=(
        "contracts/stable-locator-contract-v1/ is a skeleton only "
        "(ADR-0001). No stable locator implementation exists yet to "
        "validate against."
    )
)
def test_stable_locator_is_not_a_raw_engine_id():
    raise NotImplementedError(
        "Implement once contracts/stable-locator-contract-v1/ defines a "
        "concrete schema and a reference implementation exists."
    )


@pytest.mark.skip(
    reason=(
        "contracts/stable-locator-contract-v1/ is a skeleton only "
        "(ADR-0001). No engine-replacement scenario exists yet to test."
    )
)
def test_stable_locator_survives_engine_replacement():
    raise NotImplementedError(
        "Implement once at least two engine adapters exist that can "
        "process the same document, to prove locator stability across "
        "engine swaps."
    )
