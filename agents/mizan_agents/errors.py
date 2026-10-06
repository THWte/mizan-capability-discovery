"""Shared exception type for MIZAN Agent Society v1 contract violations."""
from __future__ import annotations


class AgentContractError(ValueError):
    """Raised when an agent violates the Handoff Contract, Governed Memory
    rules, or an Architecture Guardian gate.

    Like ``contracts.mizan_contracts.errors.ContractValidationError``, this
    is a plain ``ValueError`` subclass: violations are rejected
    deterministically, never repaired implicitly or silently downgraded to
    a warning.
    """
