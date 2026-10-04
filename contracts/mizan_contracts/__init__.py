"""
MIZAN Core Contracts (A1/A2)

This package contains the real, versioned, importable, testable
implementation of MIZAN's four foundational contracts:

- canonical_v1       -- Canonical Contract v1
- provenance_v1      -- Provenance Contract v1
- identity_v1        -- Identity Contract v1
- stable_locator_v1  -- Stable Locator Contract v1

These implement docs/architecture/ARCHITECTURAL_INVARIANTS.md. The
human-readable specification for each contract lives in the matching
`contracts/<name>-contract-v1/README.md` directory; this package is the
executable, test-covered reference implementation those documents describe.

No module in this package may import, reference, or depend on any
third-party document-intelligence or retrieval engine (Docling, PaddleOCR,
MinerU, Qdrant, pgvector, or any other). Engines adapt to these contracts;
these contracts never adapt to an engine (Invariant 1, Invariant 10).
"""
from . import canonical_v1, provenance_v1, identity_v1, stable_locator_v1
from .errors import ContractValidationError

__all__ = [
    "canonical_v1",
    "provenance_v1",
    "identity_v1",
    "stable_locator_v1",
    "ContractValidationError",
]
