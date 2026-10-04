"""
Architecture validation placeholder: Retrieval is not Evidence Authority.

Validates Invariant 4 (Retrieval != Evidence Authority):
see docs/architecture/ARCHITECTURAL_INVARIANTS.md#4-retrieval--evidence-authority

Intended future assertions (once a retrieval engine, e.g. pgvector/Haystack,
and contracts/canonical-contract-v1/ exist):

1. A retrieval result (vector search hit, hybrid search hit, keyword match)
   carries a rank/score, not a verification or evidence status.
2. No API surface allows a retrieval result to be written directly into a
   Fact or Accepted Fact store without first passing through evidence
   resolution and verification.
3. A high retrieval score alone must not satisfy any assertion that a claim
   is "verified" or "evidenced" -- those require the distinct evidence/
   verification layers, not retrieval rank.

This module intentionally contains no real assertions yet: no retrieval
engine is integrated, and contracts/canonical-contract-v1/ is a skeleton.
Per architectural convention (see tests/architecture/README.md), the test
SKIPS with an explicit reason rather than being deleted or fabricated as
passing.
"""
import pytest


@pytest.mark.skip(
    reason=(
        "No retrieval engine is integrated yet (pgvector/Haystack "
        "evaluations are still pending per README.md Phase 1/2), and "
        "contracts/canonical-contract-v1/ is a skeleton only (ADR-0001)."
    )
)
def test_retrieval_result_cannot_be_written_as_accepted_fact():
    raise NotImplementedError(
        "Implement once a retrieval engine is integrated behind an "
        "adapter, to prove its output cannot bypass evidence resolution "
        "and verification."
    )


@pytest.mark.skip(
    reason=(
        "No retrieval engine is integrated yet, and "
        "contracts/canonical-contract-v1/ is a skeleton only (ADR-0001)."
    )
)
def test_high_retrieval_score_does_not_satisfy_verification_requirement():
    raise NotImplementedError(
        "Implement once MIZAN's verification layer exists, to prove rank/"
        "score alone cannot satisfy a verification check."
    )
