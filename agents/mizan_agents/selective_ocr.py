"""A28 — Selective OCR and page quality routing v1."""
from __future__ import annotations
import dataclasses
from enum import Enum
from .long_document_stream import PageInput

class PageRoute(str,Enum):
    TEXT_ONLY="TEXT_ONLY"
    OCR_ONLY="OCR_ONLY"
    TEXT_PLUS_OCR_COMPARE="TEXT_PLUS_OCR_COMPARE"
    TABLE_SPECIALIST="TABLE_SPECIALIST"
    HUMAN_REVIEW="HUMAN_REVIEW"

@dataclasses.dataclass(frozen=True,kw_only=True)
class PageQualityDecision:
    page_number:int
    route:PageRoute
    reason_codes:tuple[str,...]
    production_approved:bool=False
    def __post_init__(self):
        if self.production_approved: raise ValueError("page router cannot production-approve engines")

def route_page(page:PageInput)->PageQualityDecision:
    if page.low_quality_hint:
        return PageQualityDecision(page_number=page.page_number,route=PageRoute.HUMAN_REVIEW,reason_codes=("LOW_QUALITY_HINT",))
    if page.table_hint and (not page.has_text_layer or page.image_coverage>0.5):
        return PageQualityDecision(page_number=page.page_number,route=PageRoute.TABLE_SPECIALIST,reason_codes=("TABLE_STRUCTURE_REQUIRED","RASTER_OR_IMAGE_HEAVY",))
    if page.has_text_layer and page.image_coverage < 0.20 and len(page.raw_text.strip()) >= 40:
        return PageQualityDecision(page_number=page.page_number,route=PageRoute.TEXT_ONLY,reason_codes=("TEXT_LAYER_SUFFICIENT","OCR_SKIPPED",))
    if not page.has_text_layer and page.image_coverage >= 0.80:
        return PageQualityDecision(page_number=page.page_number,route=PageRoute.OCR_ONLY,reason_codes=("NO_TEXT_LAYER","IMAGE_DOMINANT",))
    return PageQualityDecision(page_number=page.page_number,route=PageRoute.TEXT_PLUS_OCR_COMPARE,reason_codes=("AMBIGUOUS_PAGE","EVIDENCE_COMPARISON_REQUIRED",))
