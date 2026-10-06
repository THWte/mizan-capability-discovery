"""MIZAN Legal Reasoning Foundation v1 — A13.

Produces issue analyses and hypotheses, never judgments or accepted facts.
"""
from __future__ import annotations
import dataclasses,hashlib
from .knowledge_layer import KnowledgeClaim

class ReasoningError(ValueError): pass

@dataclasses.dataclass(frozen=True,kw_only=True)
class LegalIssue:
    issue_id:str; case_id:str; question:str
    supporting_claim_ids:tuple[str,...]=()
    opposing_claim_ids:tuple[str,...]=()
    unresolved_claim_ids:tuple[str,...]=()

@dataclasses.dataclass(frozen=True,kw_only=True)
class ReasoningConclusion:
    reasoning_id:str; case_id:str; issue_id:str
    proposition:str
    support_ids:tuple[str,...]
    counter_ids:tuple[str,...]
    uncertainty:str
    requires_human_review:bool=True
    authoritative:bool=False
    outcome_prediction:bool=False
    def __post_init__(self):
        if self.authoritative: raise ReasoningError("reasoning cannot be authoritative")
        if self.outcome_prediction: raise ReasoningError("v1 does not permit outcome prediction")
        if not self.support_ids and not self.counter_ids: raise ReasoningError("reasoning must cite knowledge inputs")

def analyze_issue(issue:LegalIssue,claims:tuple[KnowledgeClaim,...],*,proposition:str)->ReasoningConclusion:
    by_id={c.knowledge_id:c for c in claims}
    refs=issue.supporting_claim_ids+issue.opposing_claim_ids+issue.unresolved_claim_ids
    missing=[x for x in refs if x not in by_id]
    if missing: raise ReasoningError(f"missing knowledge claims: {missing}")
    if any(by_id[x].case_id != issue.case_id for x in refs): raise ReasoningError("cross-case reasoning requires an explicit linking contract")
    uncertainty="HIGH" if issue.unresolved_claim_ids else ("MEDIUM" if issue.opposing_claim_ids else "LOW")
    raw=f"{issue.issue_id}|{proposition}|{'|'.join(refs)}".encode()
    return ReasoningConclusion(reasoning_id="R-"+hashlib.sha256(raw).hexdigest()[:24],case_id=issue.case_id,issue_id=issue.issue_id,proposition=proposition,support_ids=issue.supporting_claim_ids,counter_ids=issue.opposing_claim_ids+issue.unresolved_claim_ids,uncertainty=uncertainty)
