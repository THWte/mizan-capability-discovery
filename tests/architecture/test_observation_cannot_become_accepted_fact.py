"""
Architecture validation placeholder: Observation cannot become Accepted Fact
directly.

Validates Invariant 2 (Observation != Evidence != Fact != Accepted Fact):
see docs/architecture/ARCHITECTURAL_INVARIANTS.md#2-observation--evidence--fact--accepted-fact

This is the most directly testable invariant today because the Docling
sandbox (sandboxes/docling/adapter.py) already implements the first two
pipeline stages (RAW EXTRACTION / NORMALIZATION) concretely. Even so, this
suite stays a placeholder here because contracts/canonical-contract-v1/
(the MIZAN-wide canonical shape, as opposed to the Docling-sandbox-local
NormalizedDocumentResult shape) does not exist yet -- validating against the
sandbox-local type would not actually prove the MIZAN-wide invariant holds
for every engine, only for Docling.

Intended future assertions (once contracts/canonical-contract-v1/ has a
concrete schema and a reference implementation exists):

1. No adapter-produced object (regardless of engine) exposes a code path
   that marks its own output as "Accepted Fact" -- that status can only be
   set by MIZAN's verification layer, never by an adapter or engine.
2. An Observation (raw engine output) passed into the canonical contract is
   tagged at the Observation/Evidence stage, never pre-tagged as Fact or
   Accepted Fact by the adapter itself.
3. Promotion from Evidence to Fact, and from Fact to Accepted Fact, requires
   an explicit call into MIZAN's interpretation/verification layers; there
   is no default or implicit promotion path.

This module intentionally contains no real assertions yet against the
MIZAN-wide canonical contract. Per architectural convention (see
tests/architecture/README.md), the test SKIPS with an explicit reason rather
than being deleted or fabricated as passing.
"""
import pytest


@pytest.mark.skip(
    reason=(
        "contracts/canonical-contract-v1/ is a skeleton only (ADR-0001). "
        "Validating this invariant against the Docling-sandbox-local "
        "NormalizedDocumentResult type alone would not prove the "
        "MIZAN-wide invariant for every engine."
    )
)
def test_adapter_output_cannot_self_report_as_accepted_fact():
    raise NotImplementedError(
        "Implement once contracts/canonical-contract-v1/ defines a "
        "concrete schema shared across engine adapters."
    )


@pytest.mark.skip(
    reason=(
        "MIZAN's interpretation/verification layers do not exist yet to "
        "validate the explicit-promotion-only requirement."
    )
)
def test_promotion_from_evidence_to_accepted_fact_requires_explicit_verification_call():
    raise NotImplementedError(
        "Implement once MIZAN's interpretation/verification layers exist."
    )
