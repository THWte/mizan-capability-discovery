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
from .document_authority import AuthorityPage, AuthoritySegment, AuthorityKind, classify_authority_pages, build_authority_segments

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
    authority_pages: tuple[AuthorityPage, ...]=()
    authority_segments: tuple[AuthoritySegment, ...]=()

    def __post_init__(self):
        if self.accepted_fact_count != 0:
            raise IngestionError("A33 cannot create Accepted Facts")
        if self.page_count != len(self.pages):
            raise IngestionError("page count mismatch")

_CASE_RE=re.compile(r"(?:رقم\s*(?:القضية|الدعوى)\s*[:：-]?\s*)([0-9٠-٩]{6,14})")
_JUDGMENT_RE=re.compile(r"(?:رقم\s*(?:الحكم|الصك)\s*[:：-]?\s*)([0-9٠-٩]{5,14})")
_NUMERIC_ID_RE=re.compile(r"(?<![0-9٠-٩])([0-9٠-٩]{5,14})(?![0-9٠-٩])")
_ARABIC_LABELS={
    ExtractionKind.CASE_NUMBER: ("رقم القضية","القضية","رقم الدعوى","الدعوى"),
    ExtractionKind.JUDGMENT_NUMBER: ("رقم الحكم","الحكم","رقم الصك","الصك"),
}

def _arabic_letters(s:str)->str:
    # PDF text extractors may alter whitespace/directionality. Keep Arabic
    # letters only so label matching is resilient without inventing values.
    return "".join(ch for ch in s if "\u0600" <= ch <= "\u06ff")

def _label_present(text:str,kind:ExtractionKind)->bool:
    letters=_arabic_letters(text)
    return any(_arabic_letters(label) in letters for label in _ARABIC_LABELS[kind])
_DATE_RE=re.compile(r"(?<!\d)(\d{1,2}[-/]\d{1,2}[-/]\d{4}|\d{4}[-/]\d{1,2}[-/]\d{1,2})(?!\d)")
_AMOUNT_RE=re.compile(r"(?<!\d)(\d[\d,]*(?:\.\d{1,2})?)(?=[\s\S]{0,24}(?:ريال|ر\.س))")
_MACHINE_CASE_RE=re.compile(r"CASE_NUMBER\s*[:=-]?\s*([0-9]{6,14})",re.I)
_MACHINE_JUDGMENT_RE=re.compile(r"JUDGMENT_NUMBER\s*[:=-]?\s*([0-9]{5,14})",re.I)
_MACHINE_DATE_RE=re.compile(r"DATE\s*[:=-]?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{4})",re.I)
_MACHINE_AMOUNT_RE=re.compile(r"AMOUNT\s*[:=-]?\s*(\d[\d,.]*)",re.I)
_COURT_RE=re.compile(r"((?:المحكمة|محكمة)\s+[\u0600-\u06FF\s]{3,80})")
_CIRCUIT_RE=re.compile(r"((?:الدائرة)\s+[\u0600-\u06FF\s0-9٠-٩]{2,60})")

def _candidate(kind, value, page_number, span_id, confidence):
    return ExtractedCandidate(kind=kind,value=value.strip(),page_number=page_number,span_id=span_id,confidence=confidence)

_CURRENCY_RE=re.compile(r"(?:ر\s*ي\s*ا\s*ل|ر\s*\.?\s*س)",re.I)
_AMOUNT_TOKEN_RE=re.compile(r"(?<![0-9٠-٩])([0-9٠-٩][0-9٠-٩,٬]*(?:[.٫][0-9٠-٩]{1,2})?)(?![0-9٠-٩])")
# Canonical Arabic legal amount-introducing labels. Used as a fallback binding
# when the currency word itself is destroyed by a broken PDF text layer
# (e.g. Chromium headless reorders "ريال" into "لاير"). Binding is strictly
# label-gated: a bare number is never promoted to an amount candidate.
_AMOUNT_LABELS=("مبلغ","مقدار")
_AMOUNT_LABEL_WINDOW_LEFT=64
_AMOUNT_LABEL_WINDOW_RIGHT=24

def _resolve_label_amounts(page_number:int,spans:tuple)->tuple[ExtractedCandidate,...]:
    """Bind a number to an explicit amount label when the currency word is
    unreadable. Windows are asymmetric because the label usually introduces the
    figure ("بمبلغ 12500 ريال") even when extraction reorders the line. The
    same rejections as the currency resolver apply: date-like or
    identifier-like tokens are never treated as amounts."""
    if not spans: return ()
    page_text="\n".join(s.text for s in spans)
    out=[]
    seen=set()
    for lbl in re.finditer("|".join(re.escape(w) for w in _AMOUNT_LABELS),page_text):
        left_start=max(0,lbl.start()-_AMOUNT_LABEL_WINDOW_LEFT)
        right_end=min(len(page_text),lbl.end()+_AMOUNT_LABEL_WINDOW_RIGHT)
        candidates=[]
        left_nums=list(_AMOUNT_TOKEN_RE.finditer(page_text[left_start:lbl.start()]))
        if left_nums:
            m=left_nums[-1]
            candidates.append((m.group(1),left_start+m.start(1),lbl.start()-(left_start+m.end(1))))
        right_nums=list(_AMOUNT_TOKEN_RE.finditer(page_text[lbl.end():right_end]))
        if right_nums:
            m=right_nums[0]
            candidates.append((m.group(1),lbl.end()+m.start(1),m.start(1)))
        if not candidates: continue
        value,absolute,_distance=min(candidates,key=lambda x:x[2])
        digits=re.sub(r"[^0-9٠-٩]","",value)
        if "-" in value or "/" in value or len(digits)>12: continue
        # Reject numeric fragments that are glued to a date-like sequence
        # ("18-04-1448" must not yield "1448" as an amount).
        _before=page_text[absolute-1] if absolute>0 else ""
        _after=page_text[absolute+len(value)] if absolute+len(value)<len(page_text) else ""
        if (_before and _before in "-/") or (_after and _after in "-/"): continue
        owner=next((s for s in spans if s.start_offset<=absolute<s.end_offset),spans[0])
        key=(value,owner.span_id)
        if key not in seen:
            out.append(_candidate(ExtractionKind.AMOUNT,value,page_number,owner.span_id,.85))
            seen.add(key)
    return tuple(out)

def _resolve_page_amounts(page_number:int,spans:tuple[LegalSpan,...])->tuple[ExtractedCandidate,...]:
    """Resolve amounts across span/line boundaries without accepting bare numbers."""
    if not spans: return ()
    page_text="\n".join(s.text for s in spans)
    out=[]
    seen=set()
    for cur in _CURRENCY_RE.finditer(page_text):
        left_start=max(0,cur.start()-64)
        right_end=min(len(page_text),cur.end()+64)
        left=page_text[left_start:cur.start()]
        right=page_text[cur.end():right_end]
        candidates=[]
        left_nums=list(_AMOUNT_TOKEN_RE.finditer(left))
        if left_nums:
            m=left_nums[-1]
            candidates.append((m.group(1),left_start+m.start(1),cur.start()-(left_start+m.end(1))))
        right_nums=list(_AMOUNT_TOKEN_RE.finditer(right))
        if right_nums:
            m=right_nums[0]
            candidates.append((m.group(1),cur.end()+m.start(1),m.start(1)))
        if not candidates: continue
        value,absolute,_distance=min(candidates,key=lambda x:x[2])
        # Reject date-like or identifier-like tokens; currency proximity alone
        # must not turn a case/judgment number into an amount.
        digits=re.sub(r"[^0-9٠-٩]","",value)
        if "-" in value or "/" in value or len(digits)>12: continue
        owner=next((s for s in spans if s.start_offset<=absolute<s.end_offset),spans[0])
        key=(value,owner.span_id)
        if key not in seen:
            out.append(_candidate(ExtractionKind.AMOUNT,value,page_number,owner.span_id,.88))
            seen.add(key)
    return tuple(out)

def extract_legal_candidates(page_number:int, spans:tuple[LegalSpan,...])->tuple[ExtractedCandidate,...]:
    out=list(_resolve_page_amounts(page_number,spans))+list(_resolve_label_amounts(page_number,spans))
    for s in spans:
        txt=s.text
        case_hits=list(_CASE_RE.finditer(txt))
        judgment_hits=list(_JUDGMENT_RE.finditer(txt))
        for m in _MACHINE_CASE_RE.finditer(txt): out.append(_candidate(ExtractionKind.CASE_NUMBER,m.group(1),page_number,s.span_id,.95))
        for m in _MACHINE_JUDGMENT_RE.finditer(txt): out.append(_candidate(ExtractionKind.JUDGMENT_NUMBER,m.group(1),page_number,s.span_id,.92))
        for m in _MACHINE_DATE_RE.finditer(txt): out.append(_candidate(ExtractionKind.DATE,m.group(1),page_number,s.span_id,.90))
        for m in _MACHINE_AMOUNT_RE.finditer(txt): out.append(_candidate(ExtractionKind.AMOUNT,m.group(1),page_number,s.span_id,.90))
        for m in case_hits: out.append(_candidate(ExtractionKind.CASE_NUMBER,m.group(1),page_number,s.span_id,.95))
        for m in judgment_hits: out.append(_candidate(ExtractionKind.JUDGMENT_NUMBER,m.group(1),page_number,s.span_id,.92))
        # Fallback for PDF extractors that disturb Arabic spacing/direction:
        # only bind a numeric identifier when the corresponding Arabic label
        # remains detectable in the same traceable span.
        ids=[m.group(1) for m in _NUMERIC_ID_RE.finditer(txt)]
        reserved={m.group(1) for m in case_hits+judgment_hits}
        ids=[x for x in ids if x not in reserved]
        if not case_hits and _label_present(txt,ExtractionKind.CASE_NUMBER) and ids:
            out.append(_candidate(ExtractionKind.CASE_NUMBER,ids[0],page_number,s.span_id,.82))
            ids=ids[1:]
        if not judgment_hits and _label_present(txt,ExtractionKind.JUDGMENT_NUMBER) and ids:
            out.append(_candidate(ExtractionKind.JUDGMENT_NUMBER,ids[0],page_number,s.span_id,.80))
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
        # A33 direct-text-first override: a real PDF text layer is authoritative
        # for extraction routing even when the page is short. A28's <40-char
        # ambiguity heuristic is useful for generic routing, but must not cause
        # needless OCR of headings/short legal pages.
        if p.has_text_layer and p.raw_text.strip() and decision.route is PageRoute.TEXT_PLUS_OCR_COMPARE:
            decision=dataclasses.replace(decision,route=PageRoute.TEXT_ONLY,reason_codes=("TEXT_LAYER_PRESENT","A33_DIRECT_TEXT_FIRST"))
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

    authority_pages=classify_authority_pages((p.page_number,p.raw_text) for p in ingested)
    authority_segments=build_authority_segments(authority_pages)
    return IngestedLegalDocument(
        document_id=document_id,source_sha256=source_sha,page_count=len(inputs),
        pages=tuple(ingested),ocr_pages=tuple(sorted(set(ocr_pages))),
        human_review_pages=tuple(sorted(set(review_pages))),
        authority_pages=authority_pages,authority_segments=authority_segments,
    )
