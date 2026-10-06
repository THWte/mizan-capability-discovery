"""Dedicated verification gate between Candidate Fact and Accepted Fact."""
from __future__ import annotations
import dataclasses,hashlib
from .knowledge_layer import KnowledgeClaim,KnowledgeType,KnowledgeError

class VerificationError(ValueError): pass

@dataclasses.dataclass(frozen=True,kw_only=True)
class VerificationDecision:
    verification_id:str
    candidate_knowledge_id:str
    case_id:str
    outcome:str  # VERIFIED / REJECTED / REVIEW_REQUIRED
    verifier:str
    rationale:str
    source_citations:tuple[str,...]
    accepted_fact_id:str|None=None
    def __post_init__(self):
        if self.outcome not in {"VERIFIED","REJECTED","REVIEW_REQUIRED"}: raise VerificationError("invalid verification outcome")
        if self.outcome=="VERIFIED" and not self.source_citations: raise VerificationError("verification requires citations")
        if self.accepted_fact_id is not None: raise VerificationError("verification decision cannot itself create Accepted Fact")

def verify_candidate(claim:KnowledgeClaim,*,verifier:str,rationale:str,source_citations:tuple[str,...],approve:bool|None)->VerificationDecision:
    if claim.knowledge_type != KnowledgeType.CANDIDATE_FACT: raise VerificationError("only CandidateFact enters fact verification")
    if claim.accepted: raise VerificationError("already accepted flag is forbidden")
    outcome="REVIEW_REQUIRED" if approve is None else ("VERIFIED" if approve else "REJECTED")
    if outcome=="VERIFIED" and not source_citations: raise VerificationError("verified candidate requires citations")
    raw=f"{claim.knowledge_id}|{outcome}|{verifier}|{rationale}".encode()
    return VerificationDecision(verification_id="V-"+hashlib.sha256(raw).hexdigest()[:24],candidate_knowledge_id=claim.knowledge_id,case_id=claim.case_id,outcome=outcome,verifier=verifier,rationale=rationale,source_citations=source_citations)
