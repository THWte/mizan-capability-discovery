"""MIZAN Production Readiness Gate v1 — A16."""
from __future__ import annotations
import dataclasses
from enum import Enum
from .golden_dataset import GoldenDatasetManifest, production_eligible_dataset
from .capability_registry import CapabilityRecord


class ReadinessStatus(str,Enum):
    READY="READY"
    CONDITIONAL="CONDITIONAL"
    NOT_READY="NOT_READY"


@dataclasses.dataclass(frozen=True,kw_only=True)
class ProductionReadinessInput:
    golden_dataset:GoldenDatasetManifest
    capabilities:tuple[CapabilityRecord,...]
    reverse_traceability_accuracy:float
    citation_accuracy:float
    critical_test_failures:int
    unresolved_security_blockers:tuple[str,...]=()
    runtime_integration_verified:bool=False


@dataclasses.dataclass(frozen=True,kw_only=True)
class ProductionReadinessDecision:
    status:ReadinessStatus
    blockers:tuple[str,...]
    warnings:tuple[str,...]
    production_approved:bool


def assess_production_readiness(inp:ProductionReadinessInput)->ProductionReadinessDecision:
    blockers=[]
    warnings=[]
    if not production_eligible_dataset(inp.golden_dataset):
        blockers.append("NON_SYNTHETIC_INDEPENDENTLY_REVIEWED_GOLDEN_DATASET_REQUIRED")
    if inp.reverse_traceability_accuracy < 1.0:
        blockers.append("REVERSE_TRACEABILITY_MUST_BE_100_PERCENT")
    if inp.citation_accuracy < 1.0:
        blockers.append("CITATION_ACCURACY_MUST_BE_100_PERCENT")
    if inp.critical_test_failures:
        blockers.append("CRITICAL_TEST_FAILURES_PRESENT")
    if not inp.runtime_integration_verified:
        blockers.append("RUNTIME_INTEGRATION_NOT_VERIFIED")
    blockers.extend(inp.unresolved_security_blockers)
    for cap in inp.capabilities:
        if not cap.production_approved:
            warnings.append(f"{cap.provider}:{cap.capability}:NOT_PRODUCTION_APPROVED")
        blockers.extend(f"{cap.provider}:{b}" for b in cap.blockers if "UNRESOLVED" in b or "UNSAFE" in b or "BELOW_THRESHOLD" in b)
    blockers=tuple(dict.fromkeys(blockers))
    warnings=tuple(dict.fromkeys(warnings))
    status=ReadinessStatus.READY if not blockers else ReadinessStatus.NOT_READY
    return ProductionReadinessDecision(status=status,blockers=blockers,warnings=warnings,production_approved=(status is ReadinessStatus.READY))
