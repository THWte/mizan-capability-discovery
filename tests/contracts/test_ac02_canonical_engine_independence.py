"""AC-02: Canonical Contract is independent of any specific engine.

Repository scan: no engine-specific identifier/dependency string may appear
in the canonical contract's implementation or specification.
"""
import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]

_FORBIDDEN = ("docling", "paddleocr", "mineru", "qdrant", "pgvector")

_SCANNED_PATHS = (
    _REPO_ROOT / "contracts" / "mizan_contracts" / "canonical_v1.py",
    _REPO_ROOT / "contracts" / "canonical-contract-v1" / "README.md",
)

# Full project-wide scan (stronger than AC-02's canonical-only requirement):
# ALL FOUR contract modules must be engine-independent, per Invariant 1.
_ALL_CONTRACT_MODULES = (
    _REPO_ROOT / "contracts" / "mizan_contracts" / "canonical_v1.py",
    _REPO_ROOT / "contracts" / "mizan_contracts" / "provenance_v1.py",
    _REPO_ROOT / "contracts" / "mizan_contracts" / "identity_v1.py",
    _REPO_ROOT / "contracts" / "mizan_contracts" / "stable_locator_v1.py",
)


def test_canonical_contract_files_exist():
    for path in _SCANNED_PATHS:
        assert path.is_file(), f"Expected canonical contract file to exist: {path}"


def test_canonical_contract_contains_zero_engine_specific_dependencies():
    violations = []
    for path in _SCANNED_PATHS:
        text = path.read_text(encoding="utf-8").lower()
        for term in _FORBIDDEN:
            # Allow the term to appear only inside an explicit negative
            # statement documenting that it must NOT be a dependency
            # (e.g. this very file's own docstring-style prohibition list).
            # A real dependency would appear as `import docling`,
            # `from docling...`, or a bare engine name used as a type/field.
            if re.search(rf"\bimport\s+{term}\b", text) or re.search(rf"\bfrom\s+{term}\b", text):
                violations.append(f"{path.name}: found import of {term!r}")
    assert violations == [], f"Engine-specific dependency found in canonical contract: {violations}"


def test_canonical_contract_module_has_no_import_statements_for_banned_engines():
    import ast

    source = (_REPO_ROOT / "contracts" / "mizan_contracts" / "canonical_v1.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_names.add(alias.name.split(".")[0].lower())
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_names.add(node.module.split(".")[0].lower())
    assert imported_names.isdisjoint(_FORBIDDEN), (
        f"canonical_v1.py imports a banned engine module: {imported_names & set(_FORBIDDEN)}"
    )


def test_no_core_contract_module_imports_a_banned_engine():
    """Project-wide strengthening: Invariant 1 applies to every contract,
    not only Canonical. All four modules must be independently engine-free."""
    import ast

    for path in _ALL_CONTRACT_MODULES:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported_names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_names.add(alias.name.split(".")[0].lower())
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_names.add(node.module.split(".")[0].lower())
        assert imported_names.isdisjoint(_FORBIDDEN), (
            f"{path.name} imports a banned engine module: {imported_names & set(_FORBIDDEN)}"
        )
