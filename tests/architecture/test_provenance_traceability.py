"""
Architecture validation placeholder: Provenance traceability.

Validates Invariant 7 (Complete Reverse Traceability) and Invariant 6
(Evidence Resolution Does Not Create Truth):
see docs/architecture/ARCHITECTURAL_INVARIANTS.md#7-complete-reverse-traceability
see docs/architecture/ARCHITECTURAL_INVARIANTS.md#6-evidence-resolution-does-not-create-truth

Intended future assertions (once contracts/provenance-contract-v1/ has a
concrete schema and a reference implementation exists):

1. Every record reaching "Accepted Fact" status carries a provenance chain
   that can be walked backward, without gaps, to: Fact -> Evidence ->
   Raw Extraction -> Source.
2. Each link in that chain identifies which engine, which engine
   version/configuration (e.g. OCR language setting, model version), and
   which adapter produced it.
3. A record missing any link in that chain cannot be marked Accepted Fact
   (the pipeline must reject it, not silently accept it with a gap).
4. Resolving evidence for a claim (finding the supporting text/table/region)
   does not by itself change that claim's verification status -- resolution
   and verification are tracked as distinct steps with distinct timestamps
   and actors.

This module intentionally contains no real assertions yet: there is no
provenance-contract implementation to validate. Per architectural convention
(see tests/architecture/README.md), the test SKIPS with an explicit reason
rather than being deleted or fabricated as passing.
"""
import pytest


@pytest.mark.skip(
    reason=(
        "contracts/provenance-contract-v1/ is a skeleton only (ADR-0001). "
        "No provenance-chain implementation exists yet to validate "
        "against."
    )
)
def test_accepted_fact_has_unbroken_provenance_chain_to_source():
    raise NotImplementedError(
        "Implement once contracts/provenance-contract-v1/ defines a "
        "concrete schema and a reference implementation exists."
    )


@pytest.mark.skip(
    reason=(
        "contracts/provenance-contract-v1/ is a skeleton only (ADR-0001). "
        "No verification-layer implementation exists yet to test against."
    )
)
def test_evidence_resolution_alone_does_not_change_verification_status():
    raise NotImplementedError(
        "Implement once MIZAN's interpretation/verification layers exist "
        "and can be exercised against a known evidence-resolution result."
    )
