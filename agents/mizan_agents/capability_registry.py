"""MIZAN Capability Registry v1 — A17."""
from __future__ import annotations
import dataclasses
from enum import Enum


class CapabilityDecision(str,Enum):
    REUSE="REUSE"; EXTEND="EXTEND"; CONNECT="CONNECT"; CONTINUE_BENCHMARKING="CONTINUE_BENCHMARKING"; REJECT="REJECT"


@dataclasses.dataclass(frozen=True,kw_only=True)
class CapabilityRecord:
    capability:str
    provider:str
    source_ref:str
    decision:CapabilityDecision
    evidence_level:str
    benchmark_status:str
    invariant_compliance:str
    contract_compliance:str
    production_approved:bool
    blockers:tuple[str,...]=()


REGISTRY=(
    CapabilityRecord(
        capability="document_structure_parsing",provider="Docling",source_ref="PR #2",
        decision=CapabilityDecision.EXTEND,evidence_level="SANDBOX_MEASURED",
        benchmark_status="CONDITIONAL_PASS",invariant_compliance="PASS_WITH_OPEN_RUNTIME_RISK",
        contract_compliance="AC-D01..AC-D12 PASS",production_approved=False,
        blockers=("WINDOWS_STABILITY_UNRESOLVED","SCANNED_ARABIC_OCR_BELOW_THRESHOLD"),
    ),
    CapabilityRecord(
        capability="arabic_scanned_ocr",provider="PaddleOCR",source_ref="PR #5",
        decision=CapabilityDecision.CONNECT,evidence_level="SANDBOX_MEASURED",
        benchmark_status="CONDITIONAL_PASS",invariant_compliance="PASS_WITH_OPEN_RUNTIME_RISK",
        contract_compliance="PASS",production_approved=False,
        blockers=("WINDOWS_SEQUENTIAL_STABILITY_UNRESOLVED","CONCURRENT_CONVERT_UNSAFE"),
    ),
    CapabilityRecord(
        capability="vector_store",provider="pgvector",source_ref="A9",
        decision=CapabilityDecision.EXTEND,evidence_level="MEASURED_SYNTHETIC",
        benchmark_status="PASS",invariant_compliance="PASS",
        contract_compliance="RETRIEVAL_NON_AUTHORITY",production_approved=False,
        blockers=("REAL_GOLDEN_DATASET_REQUIRED",),
    ),
    CapabilityRecord(
        capability="embedding",provider="BAAI/bge-m3",source_ref="A10",
        decision=CapabilityDecision.EXTEND,evidence_level="MEASURED_SYNTHETIC",
        benchmark_status="PASS",invariant_compliance="PASS",
        contract_compliance="RETRIEVAL_NON_AUTHORITY",production_approved=False,
        blockers=("REAL_GOLDEN_DATASET_REQUIRED","APPELLATE_OUTCOME_ERRORS_OBSERVED"),
    ),
)


def find_capability(capability:str)->tuple[CapabilityRecord,...]:
    return tuple(r for r in REGISTRY if r.capability==capability)
