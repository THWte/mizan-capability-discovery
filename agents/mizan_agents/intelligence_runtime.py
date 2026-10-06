"""MIZAN Intelligence Runtime v1 — A14.

Composes already-governed layers after canonical extraction. It does not execute
external document engines and it cannot create Accepted Facts.
"""
from __future__ import annotations
import dataclasses

from .canonical_document_flow import CanonicalDocumentFlowResult
from .citation_engine import CitationRecord
from .evidence_resolution import EvidenceState
from .knowledge_layer import KnowledgeClaim, KnowledgeType, propose_claim
from .legal_reasoning import LegalIssue, ReasoningConclusion, analyze_issue
from .retrieval_fabric import RetrievalCandidate, RetrievalFabric, RetrievalQuery, RetrievalResult


class RuntimeIntegrationError(ValueError):
    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class RuntimeDocumentPacket:
    case_id: str
    flow: CanonicalDocumentFlowResult
    citations: tuple[CitationRecord, ...]
    observation_text: str

    def __post_init__(self) -> None:
        if not self.case_id:
            raise RuntimeIntegrationError("case_id is required")
        if not self.citations:
            raise RuntimeIntegrationError("at least one citation is required")
        if any(c.document_id != self.flow.document_id for c in self.citations):
            raise RuntimeIntegrationError("citation/document mismatch")
        if any(c.source_sha256 != self.flow.source_sha256 for c in self.citations):
            raise RuntimeIntegrationError("citation/source SHA mismatch")


@dataclasses.dataclass(frozen=True, kw_only=True)
class RuntimeKnowledgePacket:
    document: RuntimeDocumentPacket
    claims: tuple[KnowledgeClaim, ...]
    reasoning: tuple[ReasoningConclusion, ...] = ()
    accepted_fact_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.accepted_fact_ids:
            raise RuntimeIntegrationError("A14 runtime cannot create Accepted Facts")
        if any(c.case_id != self.document.case_id for c in self.claims):
            raise RuntimeIntegrationError("claim crossed case boundary")


def document_to_retrieval_candidate(packet: RuntimeDocumentPacket) -> RetrievalCandidate:
    citation = packet.citations[0]
    return RetrievalCandidate(
        candidate_id=f"RET-{citation.citation_id}",
        text=packet.observation_text,
        span_locator=citation.span_locator,
        citation_id=citation.citation_id,
        source_artifact_id=citation.source_artifact_id,
        document_id=citation.document_id,
        metadata={"case_id": packet.case_id},
    )


def propose_candidate_fact(
    packet: RuntimeDocumentPacket,
    *,
    statement: str,
    confidence: float,
) -> KnowledgeClaim:
    return propose_claim(
        kind=KnowledgeType.CANDIDATE_FACT,
        statement=statement,
        case_id=packet.case_id,
        resolution=packet.flow.evidence_resolution,
        citation_ids=tuple(c.citation_id for c in packet.citations),
        confidence=confidence,
    )


def search_case(
    *,
    query: str,
    packets: tuple[RuntimeDocumentPacket, ...],
    fabric: RetrievalFabric,
    top_k: int = 10,
) -> RetrievalResult:
    case_ids={p.case_id for p in packets}
    if len(case_ids) != 1:
        raise RuntimeIntegrationError("runtime case search requires exactly one case scope")
    candidates=tuple(document_to_retrieval_candidate(p) for p in packets)
    return fabric.search(
        RetrievalQuery(text=query,case_scope=tuple(case_ids),top_k=top_k),
        candidates,
    )


def reason_about_issue(
    packet: RuntimeKnowledgePacket,
    *,
    issue_id: str,
    question: str,
    supporting: tuple[str, ...],
    opposing: tuple[str, ...] = (),
    unresolved: tuple[str, ...] = (),
    proposition: str,
) -> ReasoningConclusion:
    issue=LegalIssue(
        issue_id=issue_id,
        case_id=packet.document.case_id,
        question=question,
        supporting_claim_ids=supporting,
        opposing_claim_ids=opposing,
        unresolved_claim_ids=unresolved,
    )
    return analyze_issue(issue,packet.claims,proposition=proposition)
