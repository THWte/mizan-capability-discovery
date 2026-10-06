"""
MIZAN Agent Society v1 - Canonical Digest

Deterministic canonical-JSON + SHA-256 digest of a Handoff payload, used to
bind a ``GuardianApproval`` (``guardian_approval.py``) to the *exact*
payload the Architecture Guardian reviewed (PART 9 / PART 12 / PART 13 of
the v1.1 hardening directive).

If a payload is mutated after review -- even a nested, mutable dict or
list inside an otherwise-frozen ``Handoff`` -- recomputing this digest at
``MasterOrchestrator.complete()`` time will no longer match the digest
recorded on the approval, and completion is blocked. This is the project's
chosen defense against the TOCTOU (time-of-check-to-time-of-use) class of
attack: no cryptographic signing is used, because that would be false
security theater in a skeleton with no private key / trust root; the real
guarantee is that completion always re-derives the digest from live state
instead of trusting a stored value.
"""
from __future__ import annotations

import hashlib
import json


def _to_jsonable(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _to_jsonable(nested) for key, nested in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(item) for item in value]
    return value


def canonical_json(value: object) -> str:
    """Deterministic JSON serialization: sorted keys, explicit separators,
    UTF-8-safe. Tuples and lists serialize identically -- JSON itself has
    no tuple type, so ``(1, 2)`` and ``[1, 2]`` are intentionally treated
    as the same canonical value."""
    return json.dumps(
        _to_jsonable(value), sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )


def canonical_digest(value: object) -> str:
    """SHA-256 hex digest of ``canonical_json(value)``, encoded as UTF-8."""
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()
