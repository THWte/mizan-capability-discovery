from __future__ import annotations
import dataclasses
from enum import Enum
from .production_readiness import ProductionReadinessDecision, ReadinessStatus
from .local_runtime_gate import LocalRuntimeManifest, verify_local_runtime

class ReleaseStage(str, Enum):
    DEVELOPMENT = "DEVELOPMENT"
    INTERNAL_RC = "INTERNAL_RC"
    PRODUCTION_RC = "PRODUCTION_RC"
    PRODUCTION = "PRODUCTION"

@dataclasses.dataclass(frozen=True, kw_only=True)
class ReleaseCandidateReport:
    commit_sha: str
    stage: ReleaseStage
    runtime_verified: bool
    production_ready: bool
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]
    release_allowed: bool

def build_release_report(*, commit_sha: str, runtime: LocalRuntimeManifest, readiness: ProductionReadinessDecision, requested_stage: ReleaseStage) -> ReleaseCandidateReport:
    runtime_ok, runtime_blockers = verify_local_runtime(runtime)
    blockers = list(runtime_blockers) + list(readiness.blockers)
    warnings = list(readiness.warnings)
    if requested_stage in (ReleaseStage.PRODUCTION_RC, ReleaseStage.PRODUCTION) and readiness.status is not ReadinessStatus.READY:
        blockers.append("PRODUCTION_READINESS_GATE_NOT_READY")
    if requested_stage is ReleaseStage.PRODUCTION and not runtime_ok:
        blockers.append("LOCAL_RUNTIME_NOT_VERIFIED")
    blockers = tuple(dict.fromkeys(blockers))
    warnings = tuple(dict.fromkeys(warnings))
    release_allowed = not blockers if requested_stage in (ReleaseStage.PRODUCTION_RC, ReleaseStage.PRODUCTION) else True
    return ReleaseCandidateReport(
        commit_sha=commit_sha,
        stage=requested_stage,
        runtime_verified=runtime_ok,
        production_ready=readiness.production_approved,
        blockers=blockers,
        warnings=warnings,
        release_allowed=release_allowed,
    )
