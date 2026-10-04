"""Shared exception type for MIZAN core contract validation failures."""
from __future__ import annotations


class ContractValidationError(ValueError):
    """Raised when an object violates a MIZAN core contract (v1) rule.

    This is intentionally a plain ValueError subclass, not a silent
    best-effort coercion: invalid objects must be rejected deterministically
    (AC-15), never repaired implicitly or accepted with a warning.
    """
