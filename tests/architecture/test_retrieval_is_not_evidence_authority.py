"""
Architecture validation: Retrieval is not Evidence Authority.

Validates Invariant 4 (Retrieval != Evidence Authority):
see docs/architecture/ARCHITECTURAL_INVARIANTS.md#4-retrieval--evidence-authority

Status update (architecture/contracts-v1): contracts/canonical-contract-v1/
and contracts/provenance-contract-v1/ now have real reference
implementations. This makes the STRUCTURAL part of this invariant
testable today, even though no retrieval engine is integrated yet: neither
contract's constructor accepts a retrieval_score/similarity/rank field at
all, so no such metadata can ever reach Evidence or Provenance state
through this API (see tests/contracts/test_ac13_*.py for the full
exercised proof). The second assertion below (an actual retrieval engine's
output attempting to satisfy a verification check) still requires a
retrieval engine integration and MIZAN's verification layer, neither of
which exist yet, and stays SKIP.
"""
import pytest

from mizan_contracts import canonical_v1, provenance_v1


def test_retrieval_result_cannot_be_written_as_accepted_fact():
    """No API surface allows a retrieval result to be written directly into
    a Fact or Accepted Fact store without first passing through evidence
    resolution and verification. Proven here structurally: neither contract
    even accepts retrieval-shaped fields, and no Fact/AcceptedFact store
    exists in this contract layer to write into."""
    with pytest.raises(TypeError):
        canonical_v1.RawObservation(
            stable_locator="MIZAN-DOC-000001/PAGE-000001/BLOCK-000001/SPAN-000001",
            raw_text="x",
            normalized_text="x",
            produced_by="retrieval-engine",
            retrieval_score=1.0,  # type: ignore[call-arg]
        )
    assert not hasattr(canonical_v1, "AcceptedFact")
    assert not hasattr(provenance_v1, "AcceptedFact")


@pytest.mark.skip(
    reason=(
        "No retrieval engine is integrated yet (pgvector/Haystack "
        "evaluations are still pending per README.md Phase 1/2), and "
        "MIZAN's verification layer does not exist yet either. The "
        "structural half of this invariant (retrieval metadata cannot "
        "reach contract state) is proven by "
        "test_retrieval_result_cannot_be_written_as_accepted_fact above and "
        "tests/contracts/test_ac13_retrieval_not_evidence_authority.py."
    )
)
def test_high_retrieval_score_does_not_satisfy_verification_requirement():
    raise NotImplementedError(
        "Implement once MIZAN's verification layer exists, to prove rank/"
        "score alone cannot satisfy a verification check."
    )
