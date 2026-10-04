"""AC-10: Observation cannot become Accepted Fact directly, by construction.

This is a structural/introspection test: it proves the forbidden path does
not exist as an API surface anywhere in the canonical contract, rather than
merely asserting a specific function call fails.
"""
import inspect

from mizan_contracts import canonical_v1


_FORBIDDEN_EXACT_NAMES = {"fact", "acceptedfact", "candidatefact", "verifiedfact"}


def test_canonical_module_defines_no_fact_or_accepted_fact_type():
    for name in dir(canonical_v1):
        if name.startswith("_"):
            continue
        lowered = name.lower()
        # Exact-name match only: "SourceArtifact" legitimately contains the
        # substring "fact" (arti-FACT) and must not be flagged.
        assert lowered not in _FORBIDDEN_EXACT_NAMES, (
            f"canonical_v1 must not define a Fact-stage type, found {name!r}."
        )


def test_raw_observation_exposes_no_promotion_method():
    forbidden_method_substrings = ("to_fact", "to_accepted_fact", "accept", "verify", "promote")
    members = [name for name, _ in inspect.getmembers(canonical_v1.RawObservation)]
    for member in members:
        lowered = member.lower()
        for forbidden in forbidden_method_substrings:
            assert forbidden not in lowered, (
                f"RawObservation must not expose a promotion method; found {member!r} "
                f"(matches forbidden pattern {forbidden!r})."
            )


def test_raw_observation_has_no_status_field_of_any_kind():
    import dataclasses

    field_names = {f.name for f in dataclasses.fields(canonical_v1.RawObservation)}
    assert "status" not in field_names
    assert "verification_status" not in field_names
    assert "accepted" not in field_names
