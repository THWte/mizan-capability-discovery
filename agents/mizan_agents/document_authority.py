"""A33.1 — Document Authority Boundary & Mixed-Document Detection.

Classifies page ranges by source authority without promoting content to fact.
The detector is deliberately conservative: quoted memoranda inside an official
judgment do not change authority merely because the word "مذكرة" appears.
"""
from __future__ import annotations
import dataclasses
from enum import Enum
from typing import Iterable

class AuthorityKind(str,Enum):
    OFFICIAL_COURT="OFFICIAL_COURT"
    APPENDED_ANALYSIS="APPENDED_ANALYSIS"
    LAWYER_MEMORANDUM="LAWYER_MEMORANDUM"
    ATTACHMENT="ATTACHMENT"
    USER_ADDED="USER_ADDED"
    UNKNOWN="UNKNOWN"

@dataclasses.dataclass(frozen=True,kw_only=True)
class AuthorityPage:
    page_number:int
    kind:AuthorityKind
    confidence:float
    reason_codes:tuple[str,...]
    boundary_before:bool=False

@dataclasses.dataclass(frozen=True,kw_only=True)
class AuthoritySegment:
    segment_id:str
    kind:AuthorityKind
    first_page:int
    last_page:int
    confidence:float
    reason_codes:tuple[str,...]

_ANALYSIS_MARKERS=(
    "تحليل صك الحكم",
    "أعد هذا التحليل",
    "أُعد هذا التحليل",
    "هذا التحليل استناد",
    "قراءة تحليلية",
)
_OFFICIAL_START_MARKERS=("وزارة العدل","المحكمة","صك رقم")
_OFFICIAL_END_MARKERS=(
    "رئيس الدائرة القضائية",
    "عضو الدائرة",
    "يكتسب الحكم الصفة النهائية",
    "سقط حقه في طلب الاستئناف",
)
_EXTERNAL_MEMO_MARKERS=("مذكرة دفاع مستقلة","مذكرة جوابية مستقلة","مقدمة من المحامي")
_ATTACHMENT_MARKERS=("مرفق مستقل","ملحق مستندي")

def _has_any(text:str,markers:tuple[str,...])->bool:
    return any(m in text for m in markers)

def classify_authority_pages(page_texts:Iterable[tuple[int,str]])->tuple[AuthorityPage,...]:
    pages=tuple((int(n),t or "") for n,t in page_texts)
    if not pages:
        return ()
    out=[]
    current=AuthorityKind.UNKNOWN
    official_seen=False
    official_end_seen=False

    for idx,(page_no,text) in enumerate(pages):
        reasons=[]
        boundary=False
        has_analysis=_has_any(text,_ANALYSIS_MARKERS)
        official_header=sum(1 for m in _OFFICIAL_START_MARKERS if m in text)>=2
        has_official_end=_has_any(text,_OFFICIAL_END_MARKERS)

        if idx==0 and official_header:
            current=AuthorityKind.OFFICIAL_COURT
            official_seen=True
            boundary=True
            reasons.append("OFFICIAL_DOCUMENT_START")
        elif has_analysis and official_seen and official_end_seen:
            if current is not AuthorityKind.APPENDED_ANALYSIS:
                boundary=True
            current=AuthorityKind.APPENDED_ANALYSIS
            reasons.extend(("EXPLICIT_ANALYSIS_MARKER","AFTER_OFFICIAL_END"))
        elif current is AuthorityKind.APPENDED_ANALYSIS:
            reasons.append("CONTINUE_APPENDED_ANALYSIS")
        elif current is AuthorityKind.OFFICIAL_COURT:
            reasons.append("CONTINUE_OFFICIAL_SEQUENCE")
        elif _has_any(text,_EXTERNAL_MEMO_MARKERS):
            current=AuthorityKind.LAWYER_MEMORANDUM
            boundary=True
            reasons.append("EXPLICIT_EXTERNAL_MEMORANDUM")
        elif _has_any(text,_ATTACHMENT_MARKERS):
            current=AuthorityKind.ATTACHMENT
            boundary=True
            reasons.append("EXPLICIT_ATTACHMENT")
        elif official_header:
            current=AuthorityKind.OFFICIAL_COURT
            official_seen=True
            boundary=True
            reasons.append("LATE_OFFICIAL_START")
        else:
            reasons.append("NO_STRONG_AUTHORITY_SIGNAL")

        if has_official_end and current is AuthorityKind.OFFICIAL_COURT:
            official_end_seen=True
            reasons.append("OFFICIAL_END_SIGNAL")

        confidence={
            AuthorityKind.OFFICIAL_COURT:.96 if official_seen else .70,
            AuthorityKind.APPENDED_ANALYSIS:.98,
            AuthorityKind.LAWYER_MEMORANDUM:.85,
            AuthorityKind.ATTACHMENT:.85,
            AuthorityKind.USER_ADDED:.70,
            AuthorityKind.UNKNOWN:.35,
        }[current]
        out.append(AuthorityPage(
            page_number=page_no,kind=current,confidence=confidence,
            reason_codes=tuple(reasons),boundary_before=boundary,
        ))
    return tuple(out)

def build_authority_segments(pages:tuple[AuthorityPage,...])->tuple[AuthoritySegment,...]:
    if not pages:
        return ()
    groups=[]
    start=0
    for i in range(1,len(pages)):
        if pages[i].kind is not pages[i-1].kind or pages[i].boundary_before:
            groups.append(pages[start:i]); start=i
    groups.append(pages[start:])
    out=[]
    for idx,g in enumerate(groups,1):
        reasons=tuple(dict.fromkeys(r for p in g for r in p.reason_codes))
        out.append(AuthoritySegment(
            segment_id=f"AUTH-{idx:04d}",
            kind=g[0].kind,
            first_page=g[0].page_number,
            last_page=g[-1].page_number,
            confidence=min(p.confidence for p in g),
            reason_codes=reasons,
        ))
    return tuple(out)

def authority_for_page(pages:tuple[AuthorityPage,...],page_number:int)->AuthorityPage:
    for p in pages:
        if p.page_number==page_number:
            return p
    raise KeyError(page_number)
