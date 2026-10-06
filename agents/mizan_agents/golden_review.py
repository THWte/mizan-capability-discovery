from __future__ import annotations
import dataclasses
from enum import Enum

class GoldenReviewError(ValueError):
    pass

class ReviewVerdict(str, Enum):
    AGREE = "AGREE"
    DISAGREE = "DISAGREE"
    ABSTAIN = "ABSTAIN"

@dataclasses.dataclass(frozen=True, kw_only=True)
class LabelReview:
    case_id: str
    reviewer_id: str
    verdict: ReviewVerdict
    citation_ids: tuple[str, ...]
    span_locators: tuple[str, ...]
    rationale: str
    independent: bool = True

    def __post_init__(self):
        if not self.case_id or not self.reviewer_id:
            raise GoldenReviewError("case_id and reviewer_id required")
        if self.verdict is ReviewVerdict.AGREE and (not self.citation_ids or not self.span_locators):
            raise GoldenReviewError("agree review requires citation and locator labels")
        if not self.rationale:
            raise GoldenReviewError("review rationale required")

@dataclasses.dataclass(frozen=True, kw_only=True)
class AdjudicatedLabel:
    case_id: str
    citation_ids: tuple[str, ...]
    span_locators: tuple[str, ...]
    reviewer_ids: tuple[str, ...]
    adjudicator_id: str
    rationale: str
    independently_reviewed: bool = True

def adjudicate(case_id: str, reviews: tuple[LabelReview, ...], *, adjudicator_id: str, rationale: str) -> AdjudicatedLabel:
    agreeing = [r for r in reviews if r.case_id == case_id and r.independent and r.verdict is ReviewVerdict.AGREE]
    if len({r.reviewer_id for r in agreeing}) < 2:
        raise GoldenReviewError("two independent agreeing reviewers required")
    labels = {(r.citation_ids, r.span_locators) for r in agreeing}
    if len(labels) != 1:
        raise GoldenReviewError("gold labels require explicit reconciliation")
    citations, locators = next(iter(labels))
    if not adjudicator_id or not rationale:
        raise GoldenReviewError("adjudicator and rationale required")
    return AdjudicatedLabel(
        case_id=case_id,
        citation_ids=citations,
        span_locators=locators,
        reviewer_ids=tuple(sorted({r.reviewer_id for r in agreeing})),
        adjudicator_id=adjudicator_id,
        rationale=rationale,
    )
