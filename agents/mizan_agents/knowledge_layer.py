"""MIZAN Knowledge Layer v1 — A12.

Knowledge objects are typed interpretations backed by Evidence Resolution.
CandidateFact is explicitly NOT an accepted/trusted fact.
"""
from __future__ import annotations
import dataclasses, hashlib
from enum import Enum
from .evidence_resolution import EvidenceResolutionRecord, EvidenceState

class KnowledgeError(ValueError): pass
class KnowledgeType(str,Enum):
    ENTITY="ENTITY"; EVENT="EVENT"; RELATION="RELATION"; TEMPORAL_CLAIM="TEMPORAL_CLAIM"; CANDIDATE_FACT="CANDIDATE_FACT"

@dataclasses.dataclass(frozen=True,kw_only=True)
class KnowledgeClaim:
    knowledge_id:str
    knowledge_type:KnowledgeType
    statement:str
    case_id:str
    resolution_id:str
    observation_ids:tuple[str,...]
    stable_locators:tuple[str,...]
    citation_ids:tuple[str,...]
    confidence:float
    requires_verification:bool=True
    accepted:bool=False
    def __post_init__(self):
        if self.accepted: raise KnowledgeError("Knowledge Layer cannot create Accepted Fact")
        if not self.statement or not self.case_id or not self.resolution_id: raise KnowledgeError("statement, case_id and resolution_id are required")
        if not self.observation_ids or not self.stable_locators: raise KnowledgeError("traceability to observations/locators is required")
        if not (0.0 <= self.confidence <= 1.0): raise KnowledgeError("confidence must be 0..1")
        if len(set(self.case_id for _ in self.observation_ids)) != 1: raise KnowledgeError("invalid case boundary")

def _kid(kind,case_id,resolution_id,statement):
    raw=f"{kind.value}|{case_id}|{resolution_id}|{statement}".encode()
    return "K-"+hashlib.sha256(raw).hexdigest()[:24]

def propose_claim(*,kind:KnowledgeType,statement:str,case_id:str,resolution:EvidenceResolutionRecord,citation_ids:tuple[str,...]=(),confidence:float=0.5)->KnowledgeClaim:
    if resolution.state in (EvidenceState.REJECTED,):
        raise KnowledgeError("rejected evidence cannot seed a knowledge claim")
    review=resolution.requires_human_review or resolution.state in (EvidenceState.CONFLICTED,EvidenceState.UNRESOLVED,EvidenceState.REVIEW_REQUIRED)
    return KnowledgeClaim(
        knowledge_id=_kid(kind,case_id,resolution.resolution_id,statement),
        knowledge_type=kind,statement=statement,case_id=case_id,resolution_id=resolution.resolution_id,
        observation_ids=tuple(x.observation_id for x in resolution.observations),
        stable_locators=tuple(x.stable_locator for x in resolution.observations),
        citation_ids=citation_ids,confidence=confidence,requires_verification=True if kind==KnowledgeType.CANDIDATE_FACT else review,
    )

@dataclasses.dataclass(frozen=True,kw_only=True)
class Relation:
    relation_id:str; case_id:str; subject_id:str; predicate:str; object_id:str
    supporting_knowledge_ids:tuple[str,...]; inferred:bool=True
    def __post_init__(self):
        if not self.supporting_knowledge_ids: raise KnowledgeError("relation requires supporting knowledge")
