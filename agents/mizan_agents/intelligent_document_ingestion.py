"""A33 — Intelligent Document Ingestion & Extraction Experience.

One user-facing path for long legal PDFs:
PDF -> page census -> direct text extraction where available -> OCR only where
needed -> hierarchical legal segmentation -> structured legal extraction
candidates with page/locator traceability.

This layer never promotes extracted content to accepted fact.
"""
from __future__ import annotations
import dataclasses, hashlib, re
from enum import Enum
from pathlib import Path

from .long_document_stream import PageInput, PageResult, process_pages_streaming
from .selective_ocr import route_page, PageRoute
from .legal_segmentation import segment_page, LegalSpan

class IngestionError(ValueError):
    pass

class ExtractionKind(str, Enum):
    COURT="COURT"
    CIRCUIT="CIRCUIT"
    CASE_NUMBER="CASE_NUMBER"
    JUDGMENT_NUMBER="JUDGMENT_NUMBER"
    DATE="DATE"
    AMOUNT="AMOUNT"
    PARTY="PARTY"
    REQUEST="REQUEST"
    DEFENSE="DEFENSE"
    REASONING="REASONING"
    OPERATIVE_PART="OPERATIVE_PART"

@dataclasses.dataclass(frozen=True, kw_only=True)
class ExtractedCandidate:
    kind: ExtractionKind
    value: str
    page_number: int
    span_id: str
    confidence: float
    verified: bool=False

    def __post_init__(self):
        if self.verified:
            raise IngestionError("A33 extraction candidates cannot self-verify")
        if not (0.0 <= self.confidence <= 1.0):
            raise IngestionError("confidence must be 0..1")

@dataclasses.dataclass(frozen=True, kw_only=True)
class IngestedPage:
    page_number: int
    source_page_sha256: str
    route: PageRoute
    raw_text: str
    spans: tuple[LegalSpan, ...]
    extraction_candidates: tuple[ExtractedCandidate, ...]

@dataclasses.dataclass(frozen=True, kw_only=True)
class IngestedLegalDocument:
    document_id: str
    source_sha256: str
    page_count: int
    pages: tuple[IngestedPage, ...]
    ocr_pages: tuple[int, ...]
    human_review_pages: tuple[int, ...]
    raw_text_preserved: bool=True
    accepted_fact_count: int=0

    def __post_init__(self):
        if self.accepted_fact_count != 0:
            raise IngestionError("A33 cannot create Accepted Facts")
        if self.page_count != len(self.pages):
            raise IngestionError("page count mismatch")

_CASE_RE=re.compile(r"(?:رقم\s*(?:القضية|الدعوى)\s*[:：-]?\s*)([0-9٠-٩]{6,14})")
_JUDGMENT_RE=re.compile(r"(?:رقم\s*(?:الحكم|الصك)\s*[:：-]?\s*)([0-9٠-٩]{5,14})")
_DATE_RE=re.compile(r"(?<!\d)(\d{1,2}[-/]\d{1,2}[-/]\d{4}|\d{4}[-/]\d{1,2}[-/]\d{1,2})(?!\d)")
_AMOUNT_RE=re.compile(r"(?<!\d)(\d[\d,]*(?:\.\d{1,2})?)\s*(?:ريال|ر\.س)")
_COURT_RE=re.compile(r"((?:المحكمة|محكمة)\s+[\u0600-\u06FF\s]{3,80})")
_CIRCUIT_RE=re.compile(r"((?:الدائرة)\s+[\u0600-\u06FF\s0-9٠-٩]{2,60})")

def _candidate(kind, value, page_number, span_id, confidence):
    return ExtractedCandidate(kind=kind,value=value.strip(),page_number=page_number,span_id=span_id,confidence=confidence)

def extract_legal_candidates(page_number:int, spans:tuple[LegalSpan,...])->tuple[ExtractedCandidate,...]:
    out=[]
    for s in spans:
        txt=s.text
        for m in _CASE_RE.finditer(txt): out.append(_candidate(ExtractionKind.CASE_NUMBER,m.group(1),page_number,s.span_id,.95))
        for m in _JUDGMENT_RE.finditer(txt): out.append(_candidate(ExtractionKind.JUDGMENT_NUMBER,m.group(1),page_number,s.span_id,.92))
        for m in _DATE_RE.finditer(txt): out.append(_candidate(ExtractionKind.DATE,m.group(1),page_number,s.span_id,.90))
        for m in _AMOUNT_RE.finditer(txt): out.append(_candidate(ExtractionKind.AMOUNT,m.group(1),page_number,s.span_id,.90))
        for m in _COURT_RE.finditer(txt): out.append(_candidate(ExtractionKind.COURT,m.group(1),page_number,s.span_id,.82))
        for m in _CIRCUIT_RE.finditer(txt): out.append(_candidate(ExtractionKind.CIRCUIT,m.group(1),page_number,s.span_id,.82))
        section=s.section
        if section=="الطلبات" and txt.strip(): out.append(_candidate(ExtractionKind.REQUEST,txt,page_number,s.span_id,.75))
        elif section=="الدفوع" and txt.strip(): out.append(_candidate(ExtractionKind.DEFENSE,txt,page_number,s.span_id,.75))
        elif section in ("الأسباب","الحيثيات") and txt.strip(): out.append(_candidate(ExtractionKind.REASONING,txt,page_number,s.span_id,.75))
        elif section in ("المنطوق","الحكم","القرار") and txt.strip(): out.append(_candidate(ExtractionKind.OPERATIVE_PART,txt,page_number,s.span_id,.80))
    return tuple(out)

def ingest_pdf(
    *,
    pdf_path:str|Path,
    document_id:str,
    ocr_callback=None,
)->IngestedLegalDocument:
    try:
        import fitz
    except Exception as e:
        raise IngestionError("PyMuPDF is required for PDF ingestion") from e

    path=Path(pdf_path)
    source_bytes=path.read_bytes()
    source_sha=hashlib.sha256(source_bytes).hexdigest()
    doc=fitz.open(path)
    inputs=[]
    for i in range(doc.page_count):
        page=doc.load_page(i)
        text=page.get_text("text") or ""
        images=page.get_images(full=True)
        page_sha=hashlib.sha256((source_sha+f"|{i+1}|{text}|{len(images)}").encode()).hexdigest()
        inputs.append(PageInput(
            page_number=i+1,
            raw_text=text,
            source_page_sha256=page_sha,
            has_text_layer=bool(text.strip()),
            image_coverage=1.0 if (not text.strip() and images) else (0.5 if images else 0.0),
        ))
    doc.close()

    ocr_pages=[]; review_pages=[]; ingested=[]

    def processor(p:PageInput)->PageResult:
        decision=route_page(p)
        text=p.raw_text
        if decision.route in (PageRoute.OCR_ONLY,PageRoute.TEXT_PLUS_OCR_COMPARE,PageRoute.TABLE_SPECIALIST):
            ocr_pages.append(p.page_number)
            if ocr_callback is not None:
                candidate=ocr_callback(path,p.page_number)
                if candidate:
                    text=candidate
            elif not text.strip():
                review_pages.append(p.page_number)
        if decision.route is PageRoute.HUMAN_REVIEW:
            review_pages.append(p.page_number)
        spans=segment_page(p.page_number,text or "")
        result=PageResult(
            page_number=p.page_number,raw_text=text,normalized_text=text,
            source_page_sha256=p.source_page_sha256,
            page_locator=f"{document_id}/PAGE-{p.page_number:06d}",
            block_locators=tuple(s.span_id for s in spans),
        )
        ingested.append(IngestedPage(
            page_number=p.page_number,source_page_sha256=p.source_page_sha256,
            route=decision.route,raw_text=text,spans=spans,
            extraction_candidates=extract_legal_candidates(p.page_number,spans),
        ))
        return result

    for _result,_cp in process_pages_streaming(
        document_id=document_id,source_sha256=source_sha,pages=inputs,page_processor=processor
    ):
        pass

    return IngestedLegalDocument(
        document_id=document_id,source_sha256=source_sha,page_count=len(inputs),
        pages=tuple(ingested),ocr_pages=tuple(sorted(set(ocr_pages))),
        human_review_pages=tuple(sorted(set(review_pages))),
    )
