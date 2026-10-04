"""AC-14: Invariant 7 reverse traceability -- explicit distinction between
what IS implemented (structural Observation -> SHA-256 trace) and what is
NOT yet implemented (a full Accepted Fact -> ... -> SHA-256 trace, which
requires Candidate Fact / Verification / Accepted Fact layers that do not
exist in this repository yet).

This test file must never claim the Accepted Fact chain works. It reports
both results explicitly, as required by the task's AC-14 wording:

    FULL ACCEPTED-FACT TRACE: NOT YET IMPLEMENTED
    STRUCTURAL OBSERVATION TRACE: PASS/FAIL
"""
import dataclasses

from mizan_contracts import canonical_v1, provenance_v1, stable_locator_v1

_SHA256 = "3" * 64


def test_structural_observation_trace_to_sha256_is_supported():
    """Observation -> Span -> Block -> Page -> Source Artifact -> SHA-256.

    STRUCTURAL OBSERVATION TRACE: this test's own pass/fail result IS that
    evidence.
    """
    document_locator = stable_locator_v1.build_document_locator(1)
    page_locator = stable_locator_v1.build_page_locator(document_locator, 1)
    block_locator = stable_locator_v1.build_block_locator(page_locator, 1)
    span_locator = stable_locator_v1.build_span_locator(block_locator, 1)

    observation = canonical_v1.RawObservation(
        stable_locator=span_locator,
        raw_text="raw",
        normalized_text="raw",
        produced_by="test-engine",
    )

    provenance = provenance_v1.ProvenanceRecord(
        source_artifact_id="A1",
        source_sha256=_SHA256,
        document_id="D1",
        document_version_id="D1-v1",
        stable_locator=observation.stable_locator,
        engine="test-engine",
        engine_version="1.0.0",
        settings={},
        extraction_timestamp="2026-01-01T00:00:00Z",
        extraction_method="test-extraction",
    )

    source_artifact = provenance_v1.SourceArtifactRecord(source_artifact_id="A1", sha256=_SHA256)

    # Step 1: Observation -> Span (the observation's own stable_locator IS
    # the span locator; no separate lookup needed, no gap possible).
    assert observation.stable_locator == span_locator

    # Step 2: Span -> Block -> Page -> Document (walkable via the locator's
    # own hierarchical path, independent of provenance).
    stable_locator_v1.validate_hierarchy_consistency(
        document_locator, page_locator, block_locator, span_locator
    )

    # Step 3: Observation's locator -> Provenance Record -> Source Artifact
    # -> SHA-256.
    resolved_sha256 = provenance_v1.trace_to_source_sha256(provenance, source_artifact)

    assert resolved_sha256 == _SHA256


def test_full_accepted_fact_trace_is_explicitly_not_implemented():
    """FULL ACCEPTED-FACT TRACE: NOT YET IMPLEMENTED.

    This is a positive assertion, not a skip: it proves the canonical
    contract has no Candidate Fact / Accepted Fact type to trace from, so
    no test anywhere in this repository may claim an
    'Accepted Fact -> ... -> SHA-256' trace is supported.
    """
    for name in dir(canonical_v1):
        lowered = name.lower()
        assert "candidatefact" not in lowered
        assert "acceptedfact" not in lowered
    for name in dir(provenance_v1):
        lowered = name.lower()
        assert "candidatefact" not in lowered
        assert "acceptedfact" not in lowered
