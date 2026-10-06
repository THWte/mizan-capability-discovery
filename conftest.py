"""
Shared pytest configuration for MIZAN core-contract and agent-society tests.

Adds `contracts/` to sys.path so `tests/contracts/*` and
`tests/architecture/*` can `import mizan_contracts` as a normal package,
without requiring an installable distribution. This repository has no
build/packaging step yet (sandboxes/docling/ and sandboxes/paddleocr/ use
their own isolated venvs; the contracts and agents packages are pure
stdlib and deliberately have zero dependencies), so a path-based conftest
is the simplest honest solution.

Also adds `agents/` to sys.path so `tests/agents/*` can
`import mizan_agents` as a normal package. `mizan_agents` itself imports
from `mizan_contracts` (e.g. `architecture_guardian.py`,
`evidence_provenance.py`), which is why both directories must be on
sys.path together, in this order.
"""
import sys
from pathlib import Path

_CONTRACTS_DIR = Path(__file__).resolve().parent / "contracts"
if str(_CONTRACTS_DIR) not in sys.path:
    sys.path.insert(0, str(_CONTRACTS_DIR))

_AGENTS_DIR = Path(__file__).resolve().parent / "agents"
if str(_AGENTS_DIR) not in sys.path:
    sys.path.insert(0, str(_AGENTS_DIR))
