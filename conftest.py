"""
Shared pytest configuration for MIZAN core-contract tests.

Adds `contracts/` to sys.path so `tests/contracts/*` and
`tests/architecture/*` can `import mizan_contracts` as a normal package,
without requiring an installable distribution. This repository has no
build/packaging step yet (sandboxes/docling/ uses its own isolated venv;
the contracts package is pure stdlib and deliberately has zero
dependencies), so a path-based conftest is the simplest honest solution.
"""
import sys
from pathlib import Path

_CONTRACTS_DIR = Path(__file__).resolve().parent / "contracts"
if str(_CONTRACTS_DIR) not in sys.path:
    sys.path.insert(0, str(_CONTRACTS_DIR))
