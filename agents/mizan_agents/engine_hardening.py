from __future__ import annotations
import dataclasses
from enum import Enum

class EngineMode(str, Enum):
    ENABLED = "ENABLED"
    RESTRICTED = "RESTRICTED"
    DISABLED = "DISABLED"

@dataclasses.dataclass(frozen=True, kw_only=True)
class EngineHardeningPolicy:
    provider: str
    capability: str
    mode: EngineMode
    concurrency_limit: int
    process_isolation_required: bool
    production_allowed: bool
    blockers: tuple[str, ...]
    required_guards: tuple[str, ...]

POLICIES = (
    EngineHardeningPolicy(
        provider="Docling",
        capability="document_structure_parsing",
        mode=EngineMode.RESTRICTED,
        concurrency_limit=1,
        process_isolation_required=True,
        production_allowed=False,
        blockers=("WINDOWS_STABILITY_UNRESOLVED", "SCANNED_ARABIC_OCR_BELOW_THRESHOLD"),
        required_guards=("OCR_ROUTING", "NFKC", "SOURCE_SHA256", "MIZAN_BRIDGE", "FAIL_CLOSED"),
    ),
    EngineHardeningPolicy(
        provider="PaddleOCR",
        capability="arabic_scanned_ocr",
        mode=EngineMode.RESTRICTED,
        concurrency_limit=1,
        process_isolation_required=True,
        production_allowed=False,
        blockers=("WINDOWS_SEQUENTIAL_STABILITY_UNRESOLVED", "CONCURRENT_CONVERT_UNSAFE"),
        required_guards=("SERIAL_EXECUTION", "NO_CONCURRENT_CONVERT", "SOURCE_SHA256", "MIZAN_BRIDGE", "FAIL_CLOSED"),
    ),
)

def policy_for(provider: str) -> EngineHardeningPolicy:
    matches = [p for p in POLICIES if p.provider == provider]
    if len(matches) != 1:
        raise KeyError(provider)
    return matches[0]

def assert_execution_allowed(provider: str, *, concurrency: int, isolated: bool, production: bool = False) -> None:
    p = policy_for(provider)
    if p.mode is EngineMode.DISABLED:
        raise RuntimeError(f"{provider} disabled")
    if concurrency > p.concurrency_limit:
        raise RuntimeError(f"{provider} concurrency exceeds hardening policy")
    if p.process_isolation_required and not isolated:
        raise RuntimeError(f"{provider} requires process isolation")
    if production and not p.production_allowed:
        raise RuntimeError(f"{provider} is not production-approved")
