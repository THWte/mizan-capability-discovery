"""
MIZAN Agent Society v1 - Epistemic Type System

Explicit vocabulary for the epistemic status of any value flowing through
the agent society (Handoff payloads, Governed Memory values), and a
recursive validator that rejects an attempt to smuggle a *promoted* truth
status anywhere inside a nested structure -- not just at the top level.

Why this module exists (PART 4 / PART 5 of the v1.1 hardening directive):
the original ``FORBIDDEN_PAYLOAD_KEYS`` / ``FORBIDDEN_VALUE_KEYS`` checks
in ``handoff_contract.py`` and ``memory.py`` only inspected the top-level
keys of a dict. A payload like
``{"result": {"items": [{"accepted_fact": "X"}]}}`` slipped through
untouched. This module is the single, shared place both call sites use
for the (now-recursive) check, so the rule cannot drift between them.

Allowed epistemic states inside the general-purpose agent society channel
(Handoff payload / Governed Memory value):

    OBSERVATION, EVIDENCE, INFERENCE, ASSUMPTION, PROPOSAL, UNKNOWN,
    REPORTED, VERIFIED, CONFLICT

States that may **never** travel through the general Handoff Contract or
Governed Memory -- they require a dedicated, not-yet-implemented promotion
contract (Architectural Invariant 2: Observation != Evidence != Fact !=
Accepted Fact):

    CANDIDATE_FACT, FACT, VERIFIED_FACT, ACCEPTED_FACT
"""
from __future__ import annotations

from .errors import AgentContractError

# Allowed epistemic-state labels an agent may legitimately attach to a
# value (e.g. as a "state" or "epistemic_state" field). This list is
# informational/typing-only in v1 -- no code currently requires every
# payload to carry one of these labels -- but it gives agents and the
# GitHub custom agent profiles a shared, explicit vocabulary instead of
# free-text strings.
ALLOWED_EPISTEMIC_STATES = (
    "OBSERVATION",
    "EVIDENCE",
    "INFERENCE",
    "ASSUMPTION",
    "PROPOSAL",
    "UNKNOWN",
    "REPORTED",
    "VERIFIED",
    "CONFLICT",
)

# States that represent a *promoted* truth status. These are the states
# Architectural Invariant 2 says must never be reachable via the general
# Handoff Contract / Governed Memory channel -- promotion requires its own
# not-yet-implemented contract and explicit verification step.
PROMOTED_EPISTEMIC_STATES = (
    "CANDIDATE_FACT",
    "FACT",
    "VERIFIED_FACT",
    "ACCEPTED_FACT",
)

# Literal dict keys that would smuggle a promoted epistemic state through
# a payload/value, in the common casing conventions used across this
# project and its dependencies (snake_case, camelCase). This is
# deliberately an explicit, finite, exact-match list -- not a substring
# match -- so that legitimate keys such as ``artifact_id`` or
# ``satisfies_invariant`` are never falsely rejected merely for containing
# the letters "fact".
FORBIDDEN_KEYS = (
    "fact",
    "accepted_fact",
    "verified_fact",
    "candidate_fact",
    "acceptedFact",
    "verifiedFact",
    "final_fact",
    "trusted_fact",
)


def validate_no_promoted_epistemic_state(value: object, *, _path: str = "$") -> None:
    """Recursively walk ``value`` (dict / list / tuple / any nesting of
    these) and raise ``AgentContractError`` if any dict along the way
    contains a key from ``FORBIDDEN_KEYS``.

    ``_path`` is used internally to build a human-readable location for
    the error message; callers should not pass it.
    """
    if isinstance(value, dict):
        for key, nested in value.items():
            if isinstance(key, str) and key in FORBIDDEN_KEYS:
                raise AgentContractError(
                    f"Forbidden promoted-epistemic-state key {key!r} found at "
                    f"{_path}.{key}. No Handoff payload or Governed Memory "
                    "value may carry a Fact/AcceptedFact/VerifiedFact/"
                    "CandidateFact, at any nesting depth (Architectural "
                    "Invariant 2)."
                )
            validate_no_promoted_epistemic_state(nested, _path=f"{_path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            validate_no_promoted_epistemic_state(item, _path=f"{_path}[{index}]")
    # Scalars (str, int, float, bool, None, etc.) carry no nested keys and
    # are not inspected further.
