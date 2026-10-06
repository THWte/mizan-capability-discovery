"""A27 — MIZAN Long Document Streaming v1.

Streaming-first page processing for very large legal documents.
No whole-document text aggregation is required for processing or checkpoints.
"""
from __future__ import annotations
import dataclasses, hashlib, json
from pathlib import Path
from typing import Iterable, Iterator

class LongDocumentError(ValueError): pass

@dataclasses.dataclass(frozen=True,kw_only=True)
class PageInput:
    page_number:int
    raw_text:str
    source_page_sha256:str
    has_text_layer:bool=True
    image_coverage:float=0.0
    table_hint:bool=False
    low_quality_hint:bool=False

    def __post_init__(self):
        if self.page_number < 1: raise LongDocumentError("page_number must be >= 1")
        if len(self.source_page_sha256)!=64: raise LongDocumentError("page SHA-256 required")
        if not (0.0 <= self.image_coverage <= 1.0): raise LongDocumentError("image_coverage must be 0..1")

@dataclasses.dataclass(frozen=True,kw_only=True)
class PageResult:
    page_number:int
    raw_text:str
    normalized_text:str
    source_page_sha256:str
    page_locator:str
    block_locators:tuple[str,...]
    completed:bool=True

@dataclasses.dataclass(frozen=True,kw_only=True)
class Checkpoint:
    document_id:str
    source_sha256:str
    completed_pages:tuple[int,...]
    checkpoint_sha256:str

def _checkpoint_hash(document_id:str,source_sha256:str,completed_pages:tuple[int,...])->str:
    raw=json.dumps({"document_id":document_id,"source_sha256":source_sha256,"completed_pages":completed_pages},sort_keys=True,separators=(",",":")).encode()
    return hashlib.sha256(raw).hexdigest()

def make_checkpoint(document_id:str,source_sha256:str,completed_pages:Iterable[int])->Checkpoint:
    pages=tuple(sorted(set(int(x) for x in completed_pages)))
    return Checkpoint(document_id=document_id,source_sha256=source_sha256,completed_pages=pages,checkpoint_sha256=_checkpoint_hash(document_id,source_sha256,pages))

def verify_checkpoint(c:Checkpoint)->bool:
    return c.checkpoint_sha256==_checkpoint_hash(c.document_id,c.source_sha256,c.completed_pages)

def save_checkpoint(c:Checkpoint,path:str|Path)->None:
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(dataclasses.asdict(c),ensure_ascii=False,indent=2),encoding="utf-8")

def pages_to_process(pages:Iterable[PageInput],checkpoint:Checkpoint|None)->Iterator[PageInput]:
    done=set()
    if checkpoint is not None:
        if not verify_checkpoint(checkpoint): raise LongDocumentError("checkpoint integrity failed")
        done=set(checkpoint.completed_pages)
    for page in pages:
        if page.page_number not in done:
            yield page

def process_pages_streaming(
    *,
    document_id:str,
    source_sha256:str,
    pages:Iterable[PageInput],
    page_processor,
    checkpoint:Checkpoint|None=None,
    checkpoint_every:int=10,
):
    if checkpoint and (checkpoint.document_id!=document_id or checkpoint.source_sha256!=source_sha256):
        raise LongDocumentError("checkpoint belongs to another document/source")
    completed=list(checkpoint.completed_pages if checkpoint else ())
    for page in pages_to_process(pages,checkpoint):
        result=page_processor(page)
        if result.page_number != page.page_number: raise LongDocumentError("processor changed page identity")
        completed.append(page.page_number)
        current=make_checkpoint(document_id,source_sha256,completed)
        yield result,current
