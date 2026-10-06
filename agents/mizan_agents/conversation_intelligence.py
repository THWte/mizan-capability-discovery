"""
MIZAN Agent Society v1 - Conversation Intelligence Agent

Observes and classifies a user directive's intent. This agent produces an
OBSERVATION of user intent only -- it has no authority to approve, reject,
merge, or mark anything an Accepted Fact; those decisions belong to
downstream gates (Architecture Guardian, Master Orchestrator). It keeps the
same ``raw_text``/``normalized_text`` separation used throughout
``contracts/mizan_contracts/canonical_v1.py`` (Unicode NFKC), applied here
to conversational input rather than extracted document text.
"""
from __future__ import annotations

import dataclasses
import unicodedata

from .errors import AgentContractError

# Keyword -> intent mapping. Deliberately simple and deterministic (no ML
# model, no external call): this is an observation step, not an
# interpretation or verification step, and its output must remain
# reproducible (Invariant 8) and auditable.
_INTENT_KEYWORDS = (
    ("راجع", "architecture_review"),
    ("review", "architecture_review"),
    ("نفذ", "implementation"),
    ("implement", "implementation"),
    ("ارفض", "rejection"),
    ("reject", "rejection"),
    ("ادمج", "merge_request"),
    ("merge", "merge_request"),
)


def normalize(text: str) -> str:
    return unicodedata.normalize("NFKC", text)


@dataclasses.dataclass(frozen=True, kw_only=True)
class ConversationDirective:
    raw_text: str
    normalized_text: str
    intent: str
    produced_by: str = "conversation_intelligence"

    def __post_init__(self) -> None:
        if self.normalized_text != normalize(self.raw_text):
            raise AgentContractError(
                "normalized_text must equal unicodedata.normalize('NFKC', raw_text)."
            )


class ConversationIntelligenceAgent:
    def interpret(self, raw_text: str) -> ConversationDirective:
        if not raw_text or not raw_text.strip():
            raise AgentContractError("raw_text must be non-empty.")
        normalized = normalize(raw_text)
        intent = "unclassified"
        for keyword, mapped_intent in _INTENT_KEYWORDS:
            if keyword in normalized.lower() or keyword in normalized:
                intent = mapped_intent
                break
        return ConversationDirective(
            raw_text=raw_text, normalized_text=normalized, intent=intent
        )
