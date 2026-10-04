# Architecture Validation Tests (Placeholders)

**Status:** Placeholder suite — all tests are intentionally `skip`ped, not
deleted or faked as passing. They exist to make the
[Architectural Invariants](../../docs/architecture/ARCHITECTURAL_INVARIANTS.md)
mechanically checkable over time, starting from zero implementation.

## Why these are skipped, not deleted or fabricated as green

Per
[Invariant 8: Reproducibility Before Optimization](../../docs/architecture/ARCHITECTURAL_INVARIANTS.md#8-reproducibility-before-optimization)
and the general project convention established in `sandboxes/docling/`
(never hide a gap behind a workaround just to get a PASS), a test that has
nothing real to validate yet must say so explicitly (`skip` with a reason),
not be omitted or stubbed to always pass.

## Current coverage

| File | Validates | Depends on (not yet implemented) |
|---|---|---|
| `test_stable_locator_ownership.py` | Stable locators are MIZAN-owned, not engine-native IDs | `contracts/stable-locator-contract-v1/` |
| `test_provenance_traceability.py` | Every Accepted Fact traces back to Source without gaps | `contracts/provenance-contract-v1/` |
| `test_retrieval_is_not_evidence_authority.py` | A retrieval hit alone cannot be treated as evidence | `contracts/canonical-contract-v1/`, a retrieval engine integration |
| `test_observation_cannot_become_accepted_fact.py` | No adapter/engine path can shortcut Observation → Accepted Fact | `contracts/canonical-contract-v1/`, MIZAN interpretation/verification layers |

## Running

```powershell
python -m pip install pytest
python -m pytest tests/architecture -v
```

Expected result today: all tests **skip** (none pass, none fail) — this is
the correct, honest state until the corresponding contracts in `contracts/`
are actually specified and implemented. A future change should replace each
`pytest.skip(...)` with a real assertion once its dependency exists, and
remove it from the "depends on" column above.
