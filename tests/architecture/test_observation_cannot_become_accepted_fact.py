"""
Architecture validation: Observation cannot become Accepted Fact directly.

Validates Invariant 2 (Observation != Evidence != Fact != Accepted Fact):
see docs/architecture/ARCHITECTURAL_INVARIANTS.md#2-observation--evidence--fact--accepted-fact

Status update (architecture/contracts-v1): contracts/canonical-contract-v1/
now has a real reference implementation (contracts/mizan_contracts/canonical_v1.py,
also exercised directly in tests/contracts/test_ac10_*.py). The first
assertion below is now REAL: it proves, by introspection, that no adapter
output type exposes a path to self-report as Accepted Fact. The second
assertion still requires MIZAN's interpretation/verification layers, which
do not exist yet, and stays SKIP.
"""
import pytest

from mizan_contracts import canonical_v1


def test_adapter_output_cannot_self_report_as_accepted_fact():
    """No adapter-produced object exposes a code path that marks its own
    output as 'Accepted Fact' -- that status can only be set by MIZAN's
    verification layer, never by an adapter or engine."""
    # The canonical Observation entity itself: no status/promotion surface.
    _forbidden_exact_names = {"fact", "acceptedfact", "candidatefact", "verifiedfact"}
    for name in dir(canonical_v1):
        if name.startswith("_"):
            continue
        assert name.lower() not in _forbidden_exact_names, (
            f"canonical_v1 must not define a Fact-stage type, found {name!r}."
        )

    import dataclasses

    field_names = {f.name for f in dataclasses.fields(canonical_v1.RawObservation)}
    assert "status" not in field_names
    assert "accepted" not in field_names

    # And the module as a whole defines no Fact / Accepted Fact type at all.
    assert not hasattr(canonical_v1, "Fact")
    assert not hasattr(canonical_v1, "AcceptedFact")
    assert not hasattr(canonical_v1, "CandidateFact")


@pytest.mark.skip(
    reason=(
        "MIZAN's interpretation/verification layers do not exist yet to "
        "validate the explicit-promotion-only requirement (Evidence -> Fact "
        "-> Accepted Fact). contracts/mizan_contracts/ only implements the "
        "Observation stage (Invariant 2), by design, in this change."
    )
)
def test_promotion_from_evidence_to_accepted_fact_requires_explicit_verification_call():
    raise NotImplementedError(
        "Implement once MIZAN's interpretation/verification layers exist."
    )
