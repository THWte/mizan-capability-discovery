"""A29 — Hierarchical Arabic legal segmentation v1."""
from __future__ import annotations
import dataclasses,re,hashlib

_HEADINGS=("الوقائع","الأسباب","الحيثيات","المنطوق","الطلبات","الدفوع","الإجراءات","الحكم","القرار")

@dataclasses.dataclass(frozen=True,kw_only=True)
class LegalSpan:
    span_id:str
    page_number:int
    section:str
    text:str
    start_offset:int
    end_offset:int

def detect_section(line:str,current:str="UNCLASSIFIED")->str:
    norm=re.sub(r"\s+"," ",line.strip())
    for h in _HEADINGS:
        if norm==h or norm.startswith(h+" ") or norm.startswith(h+":"):
            return h
    return current

def segment_page(page_number:int,text:str,max_chars:int=1800,overlap:int=180)->tuple[LegalSpan,...]:
    if max_chars<=overlap or max_chars<200: raise ValueError("invalid segmentation window")
    section="UNCLASSIFIED"
    spans=[]
    pos=0
    for line in text.splitlines() or [text]:
        section=detect_section(line,section)
    while pos < len(text):
        end=min(len(text),pos+max_chars)
        if end < len(text):
            cut=text.rfind("\n",pos,end)
            if cut <= pos+max_chars//2:
                cut=text.rfind(" ",pos,end)
            if cut > pos:
                end=cut
        chunk=text[pos:end]
        raw=f"{page_number}|{section}|{pos}|{end}|{chunk}".encode("utf-8")
        spans.append(LegalSpan(span_id="LSPAN-"+hashlib.sha256(raw).hexdigest()[:20],page_number=page_number,section=section,text=chunk,start_offset=pos,end_offset=end))
        if end>=len(text): break
        pos=max(pos+1,end-overlap)
    return tuple(spans)

@dataclasses.dataclass(frozen=True,kw_only=True)
class DocumentSection:
    name:str
    span_ids:tuple[str,...]
    first_page:int
    last_page:int

def build_hierarchy(spans:tuple[LegalSpan,...])->tuple[DocumentSection,...]:
    groups={}
    for s in spans:
        groups.setdefault(s.section,[]).append(s)
    out=[]
    for name,items in groups.items():
        out.append(DocumentSection(name=name,span_ids=tuple(x.span_id for x in items),first_page=min(x.page_number for x in items),last_page=max(x.page_number for x in items)))
    return tuple(sorted(out,key=lambda x:(x.first_page,x.name)))
