"""
Architecture validation: Provenance traceability.

Validates Invariant 7 (Complete Reverse Traceability) and Invariant 6
(Evidence Resolution Does Not Create Truth):
see docs/architecture/ARCHITECTURAL_INVARIANTS.md#7-complete-reverse-traceability
see docs/architecture/ARCHITECTURAL_INVARIANTS.md#6-evidence-resolution-does-not-create-truth

Status update (architecture/contracts-v1): contracts/provenance-contract-v1/
now has a real reference implementation
(contracts/mizan_contracts/provenance_v1.py). This makes the STRUCTURAL
reverse-trace (Observation -> Span -> Block -> Page -> Source Artifact ->
SHA-256) real and tested -- see tests/contracts/test_ac11_*.py and
tests/contracts/test_ac14_*.py for the full exercised path.

This file intentionally still does NOT claim the FULL "Accepted Fact"
chain works (Fact -> Evidence -> Raw Extraction -> Source, ending at
Accepted Fact status) -- Candidate Fact / Verification / Accepted Fact
layers do not exist in this repository yet. That assertion stays SKIP
below, per AC-14's explicit requirement not to claim more than is
implemented.
"""
import pytest

from mizan_contracts import provenance_v1, stable_locator_v1


def test_structural_reverse_trace_from_observation_to_source_sha256_has_no_gaps():
    """Every link in Observation -> Span -> Block -> Page -> Source Artifact
    -> SHA-256 is programmatically walkable with no gap, for the
    STRUCTURAL (Observation-stage) part of this invariant. This does NOT
    prove an Accepted Fact chain -- see the SKIP'd test below."""
    document_locator = stable_locator_v1.build_document_locator(1)
    page_locator = stable_locator_v1.build_page_locator(document_locator, 1)
    block_locator = stable_locator_v1.build_block_locator(page_locator, 1)
    span_locator = stable_locator_v1.build_span_locator(block_locator, 1)

    sha256 = "7" * 64
    provenance = provenance_v1.ProvenanceRecord(
        source_artifact_id="A1",
        source_sha256=sha256,
        document_id="D1",
        document_version_id="D1-v1",
        stable_locator=span_locator,
        engine="test-engine",
        engine_version="1.0.0",
        settings={},
        extraction_timestamp="2026-01-01T00:00:00Z",
        extraction_method="test-extraction",
    )
    source_artifact = provenance_v1.SourceArtifactRecord(source_artifact_id="A1", sha256=sha256)

    resolved_sha256 = provenance_v1.trace_to_source_sha256(provenance, source_artifact)
    assert resolved_sha256 == sha256


@pytest.mark.skip(
    reason=(
        "FULL ACCEPTED-FACT TRACE: NOT YET IMPLEMENTED. MIZAN's "
        "interpretation/verification layers (Candidate Fact / Verification "
        "/ Accepted Fact) do not exist yet, so an 'Accepted Fact has an "
        "unbroken provenance chain to Source' claim would be false today. "
        "Only the structural Observation-stage trace is implemented "
        "(see test_structural_reverse_trace_from_observation_to_source_sha256_has_no_gaps "
        "above and tests/contracts/test_ac14_invariant7_reverse_traceability.py)."
    )
)
def test_accepted_fact_has_unbroken_provenance_chain_to_source():
    raise NotImplementedError(
        "Implement once Candidate Fact / Verification / Accepted Fact "
        "layers exist."
    )


@pytest.mark.skip(
    reason=(
        "contracts/provenance-contract-v1/ does not yet model an evidence-"
        "resolution step distinct from extraction/provenance recording. "
        "No verification-layer implementation exists yet to test against."
    )
)
def test_evidence_resolution_alone_does_not_change_verification_status():
    raise NotImplementedError(
        "Implement once MIZAN's interpretation/verification layers exist "
        "and can be exercised against a known evidence-resolution result."
    )
