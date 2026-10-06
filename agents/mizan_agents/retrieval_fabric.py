"""MIZAN Retrieval Fabric v1.

Hybrid candidate retrieval. Retrieval selects material for inspection; it never
creates evidence authority, fact status, or accepted truth.
"""
from __future__ import annotations
import dataclasses, re, unicodedata
from collections.abc import Callable, Iterable, Sequence

_ARABIC_DIGITS=str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹","01234567890123456789")
_TOKEN_RE=re.compile(r"[\w\u0600-\u06ff]+",re.UNICODE)
_NUM_RE=re.compile(r"(?<!\d)\d[\d,]*(?:\.\d+)?(?!\d)")
_ID_RE=re.compile(r"\b\d{7,14}\b")
_DATE_RE=re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b")
_NEG=("لا","لم","لن","ليس","غير","دون","عدم")
_FINAL=("نهائي","القطعية","مكتسب")
_APPEAL_REVERSE=("ألغت","نقض","إلغاء","نقضت","الغى")
_APPEAL_AFFIRM=("أيدت","تأييد","أبقت","أيده","ايد")

class RetrievalError(ValueError): pass

@dataclasses.dataclass(frozen=True,kw_only=True)
class RetrievalCandidate:
    candidate_id:str
    text:str
    span_locator:str
    citation_id:str
    source_artifact_id:str
    document_id:str
    metadata:dict[str,str]=dataclasses.field(default_factory=dict)
    dense_score:float=0.0
    lexical_score:float=0.0
    structured_score:float=0.0
    final_score:float=0.0
    retrieval_authority:bool=False
    fact_status:str|None=None
    def __post_init__(self):
        if self.retrieval_authority: raise RetrievalError("retrieval cannot grant evidentiary authority")
        if self.fact_status is not None: raise RetrievalError("retrieval candidate cannot carry fact status")
        if not self.span_locator or not self.citation_id: raise RetrievalError("stable span locator and citation are required")

@dataclasses.dataclass(frozen=True,kw_only=True)
class RetrievalQuery:
    text:str
    case_scope:tuple[str,...]=()
    document_scope:tuple[str,...]=()
    top_k:int=10

@dataclasses.dataclass(frozen=True,kw_only=True)
class RetrievalResult:
    query:str
    candidates:tuple[RetrievalCandidate,...]
    strategy:str="hybrid-v1"
    authoritative:bool=False
    def __post_init__(self):
        if self.authoritative: raise RetrievalError("retrieval result cannot be authoritative")

def normalize_arabic(text:str)->str:
    t=unicodedata.normalize("NFKC",text).translate(_ARABIC_DIGITS).lower()
    t=re.sub(r"[\u064b-\u065f\u0670\u0640]","",t)
    t=t.replace("أ","ا").replace("إ","ا").replace("آ","ا").replace("ى","ي")
    return re.sub(r"\s+"," ",t).strip()

def tokens(text:str)->set[str]:
    return set(_TOKEN_RE.findall(normalize_arabic(text)))

def _numbers(text:str)->set[str]:
    return {x.replace(",","") for x in _NUM_RE.findall(normalize_arabic(text))}
def _ids(text:str)->set[str]:
    return set(_ID_RE.findall(normalize_arabic(text)))
def _dates(text:str)->set[str]:
    return set(_DATE_RE.findall(normalize_arabic(text)))

def lexical_score(query:str,text:str)->float:
    q=tokens(query); d=tokens(text)
    return len(q & d)/len(q) if q else 0.0

def structured_score(query:str,text:str)->float:
    qn,dn=_numbers(query),_numbers(text); qi,di=_ids(query),_ids(text); qd,dd=_dates(query),_dates(text)
    score=0.0
    if qi: score += 3.0 if qi <= di else -3.0
    if qd: score += 2.5 if qd <= dd else -2.5
    if qn: score += 2.0 if qn <= dn else -2.0
    q=normalize_arabic(query); d=normalize_arabic(text)
    qneg=any(re.search(rf"\b{re.escape(x)}\b",q) for x in _NEG)
    dneg=any(re.search(rf"\b{re.escape(x)}\b",d) for x in _NEG)
    if qneg: score += 0.75 if dneg else -0.75
    if any(x in q for x in _APPEAL_REVERSE): score += 1.5 if any(x in d for x in _APPEAL_REVERSE) else -1.5
    if any(x in q for x in _APPEAL_AFFIRM): score += 1.5 if any(x in d for x in _APPEAL_AFFIRM) else -1.5
    if any(x in q for x in _FINAL): score += 1.0 if any(x in d for x in _FINAL) else -1.0
    return score

def _scope_ok(c:RetrievalCandidate,q:RetrievalQuery)->bool:
    if q.document_scope and c.document_id not in q.document_scope: return False
    if q.case_scope and c.metadata.get("case_id") not in q.case_scope: return False
    return True

class RetrievalFabric:
    def __init__(self, *, dense_scorer:Callable[[str,Sequence[RetrievalCandidate]],Sequence[float]]|None=None):
        self._dense=dense_scorer
    def search(self, query:RetrievalQuery, candidates:Iterable[RetrievalCandidate])->RetrievalResult:
        pool=[c for c in candidates if _scope_ok(c,query)]
        if query.top_k < 1: raise RetrievalError("top_k must be positive")
        dense=list(self._dense(query.text,pool)) if self._dense and pool else [0.0]*len(pool)
        if len(dense)!=len(pool): raise RetrievalError("dense scorer length mismatch")
        ranked=[]
        for c,ds in zip(pool,dense):
            ls=lexical_score(query.text,c.text); ss=structured_score(query.text,c.text)
            final=(0.55*float(ds))+(0.25*ls)+(0.20*ss)
            ranked.append(dataclasses.replace(c,dense_score=float(ds),lexical_score=ls,structured_score=ss,final_score=final))
        ranked.sort(key=lambda x:(x.final_score,x.structured_score,x.lexical_score,x.citation_id),reverse=True)
        return RetrievalResult(query=query.text,candidates=tuple(ranked[:query.top_k]))
