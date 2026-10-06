"""MIZAN Document Capability Routing v1.

Policy-only decision layer. It selects a capability candidate from verified
sandbox findings; it does not import Docling/PaddleOCR and does not execute
engines. Retrieval, evidence authority, and fact promotion are out of scope.
"""
from __future__ import annotations
import dataclasses
from enum import Enum


class Provider(str, Enum):
    DOCLING = "docling"
    PADDLEOCR = "paddleocr"
    NONE = "none"


class DocumentKind(str, Enum):
    PDF = "pdf"
    IMAGE = "image"
    DOCX = "docx"
    XLSX = "xlsx"
    PPTX = "pptx"


class PdfMode(str, Enum):
    BORN_DIGITAL = "born_digital"
    SCANNED = "scanned"
    AMBIGUOUS = "ambiguous"
    NOT_APPLICABLE = "not_applicable"


class RoutingStatus(str, Enum):
    CANDIDATE_ROUTE = "candidate_route"
    REVIEW_REQUIRED = "review_required"
    UNSUPPORTED = "unsupported"


@dataclasses.dataclass(frozen=True, kw_only=True)
class DocumentProfile:
    kind: DocumentKind
    pdf_mode: PdfMode = PdfMode.NOT_APPLICABLE
    arabic_expected: bool = False
    table_structure_required: bool = False
    windows_runtime: bool = True


@dataclasses.dataclass(frozen=True, kw_only=True)
class RouteDecision:
    status: RoutingStatus
    primary: Provider
    secondary: Provider = Provider.NONE
    reason_codes: tuple[str, ...] = ()
    execution_constraints: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()
    production_approved: bool = False

    def __post_init__(self) -> None:
        if self.production_approved:
            raise ValueError("Routing v1 cannot production-approve sandbox providers.")


def route_document(profile: DocumentProfile) -> RouteDecision:
    if profile.kind in (DocumentKind.DOCX, DocumentKind.XLSX, DocumentKind.PPTX):
        return RouteDecision(
            status=RoutingStatus.CANDIDATE_ROUTE,
            primary=Provider.DOCLING,
            reason_codes=("DOCLING_MULTI_FORMAT_SUPPORTED", "PADDLEOCR_FORMAT_UNSUPPORTED"),
            unresolved=("DOCLING_WINDOWS_STABILITY_UNRESOLVED",),
        )

    if profile.kind == DocumentKind.IMAGE:
        unresolved = ["PADDLEOCR_WINDOWS_SEQUENTIAL_STABILITY_UNRESOLVED"]
        if profile.table_structure_required:
            unresolved.append("SCANNED_TABLE_STRUCTURE_NOT_ESTABLISHED")
        return RouteDecision(
            status=RoutingStatus.REVIEW_REQUIRED if profile.table_structure_required else RoutingStatus.CANDIDATE_ROUTE,
            primary=Provider.PADDLEOCR,
            reason_codes=("IMAGE_REQUIRES_OCR", "PADDLEOCR_ARABIC_OCR_STRONGER_THAN_DOCLING"),
            execution_constraints=("SERIALIZED_PROCESS_ISOLATION", "NO_CONCURRENT_CONVERT"),
            unresolved=tuple(unresolved),
        )

    if profile.kind != DocumentKind.PDF:
        return RouteDecision(status=RoutingStatus.UNSUPPORTED, primary=Provider.NONE, reason_codes=("UNKNOWN_DOCUMENT_KIND",))

    if profile.pdf_mode == PdfMode.BORN_DIGITAL:
        return RouteDecision(
            status=RoutingStatus.CANDIDATE_ROUTE,
            primary=Provider.DOCLING,
            reason_codes=("DOCLING_OCR_OFF_PATH", "DOCLING_LAYOUT_STRUCTURE", "PADDLEOCR_ALWAYS_OCR"),
            unresolved=("DOCLING_WINDOWS_STABILITY_UNRESOLVED",),
        )

    if profile.pdf_mode == PdfMode.SCANNED:
        unresolved = ["PADDLEOCR_WINDOWS_SEQUENTIAL_STABILITY_UNRESOLVED"]
        if profile.table_structure_required:
            unresolved.append("SCANNED_TABLE_STRUCTURE_NOT_ESTABLISHED")
        return RouteDecision(
            status=RoutingStatus.REVIEW_REQUIRED if profile.table_structure_required else RoutingStatus.CANDIDATE_ROUTE,
            primary=Provider.PADDLEOCR,
            secondary=Provider.DOCLING if profile.table_structure_required else Provider.NONE,
            reason_codes=("SCANNED_REQUIRES_OCR", "PADDLEOCR_SHARED_ARABIC_FIXTURE_WER_0_667_VS_DOCLING_1_524"),
            execution_constraints=("SERIALIZED_PROCESS_ISOLATION", "NO_CONCURRENT_CONVERT"),
            unresolved=tuple(unresolved),
        )

    if profile.pdf_mode == PdfMode.AMBIGUOUS:
        return RouteDecision(
            status=RoutingStatus.REVIEW_REQUIRED,
            primary=Provider.DOCLING,
            secondary=Provider.PADDLEOCR if profile.arabic_expected else Provider.NONE,
            reason_codes=("AMBIGUOUS_TEXT_LAYER", "DOCLING_CAN_CLASSIFY_AND_SKIP_OR_USE_OCR"),
            execution_constraints=(("PADDLEOCR_SERIALIZED_IF_FALLBACK",) if profile.arabic_expected else ()),
            unresolved=("ENGINE_DISAGREEMENT_REQUIRES_EVIDENCE_RESOLUTION",),
        )

    return RouteDecision(
        status=RoutingStatus.REVIEW_REQUIRED,
        primary=Provider.NONE,
        reason_codes=("PDF_MODE_NOT_CLASSIFIED",),
        unresolved=("DOCUMENT_CLASSIFICATION_REQUIRED",),
    )