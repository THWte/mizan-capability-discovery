"""
MIZAN Agent Society v1 - Conversation Intelligence Agent

Observes and classifies a user directive's intent. This agent produces an
OBSERVATION of user intent only -- it has no authority to approve, reject,
merge, or mark anything an Accepted Fact; those decisions belong to
downstream gates (Architecture Guardian, Master Orchestrator). It keeps the
same ``raw_text``/``normalized_text`` separation used throughout
``contracts/mizan_contracts/canonical_v1.py`` (Unicode NFKC), applied here
to conversational input rather than extracted document text.

**Hardening (v1.1, PART 17).** A conversational message that merely
*reports* a state of the world ("PR #7 مدموج" / "PR #7 is merged") is not
the same epistemic kind of thing as an imperative instruction ("نفّذ",
"implement"), a question, a proposal, or a correction. Conflating them lets
a reported claim silently become trusted state without ever being checked
against the real system (the exact failure mode Invariant 2, Observation
!= Evidence != Fact != Accepted Fact, exists to prevent -- applied here to
conversational claims, not just document extraction). ``claim_type``,
``verification_required``, and ``confidence_class`` make this explicit and
machine-checkable: a ``REPORTED_STATE`` or ``CORRECTION`` claim is
*structurally* required to carry ``verification_required=True`` and a
non-"claim" confidence class; nothing downstream may construct a
``ConversationDirective`` that reports state without flagging it as
needing verification.
"""
from __future__ import annotations

import dataclasses
import re
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

CLAIM_TYPE_USER_DIRECTIVE = "USER_DIRECTIVE"
CLAIM_TYPE_REPORTED_STATE = "REPORTED_STATE"
CLAIM_TYPE_QUESTION = "QUESTION"
CLAIM_TYPE_PROPOSAL = "PROPOSAL"
CLAIM_TYPE_CORRECTION = "CORRECTION"

ALLOWED_CLAIM_TYPES = frozenset(
    {
        CLAIM_TYPE_USER_DIRECTIVE,
        CLAIM_TYPE_REPORTED_STATE,
        CLAIM_TYPE_QUESTION,
        CLAIM_TYPE_PROPOSAL,
        CLAIM_TYPE_CORRECTION,
    }
)

# claim_type -> (verification_required, confidence_class). This mapping is
# the single source of truth so a REPORTED_STATE/CORRECTION claim can never
# be constructed with verification_required=False by accident -- see
# __post_init__ below, which enforces it structurally rather than trusting
# the caller to pass consistent values.
_CLAIM_TYPE_SEMANTICS = {
    CLAIM_TYPE_USER_DIRECTIVE: (False, "INSTRUCTION_NOT_A_CLAIM"),
    CLAIM_TYPE_REPORTED_STATE: (True, "UNVERIFIED_REPORTED_STATE"),
    CLAIM_TYPE_QUESTION: (False, "INQUIRY_NOT_A_CLAIM"),
    CLAIM_TYPE_PROPOSAL: (False, "PROPOSAL_NOT_A_CLAIM"),
    CLAIM_TYPE_CORRECTION: (True, "UNVERIFIED_CORRECTION_CLAIM"),
}

# Word-level (not substring-level) keyword sets. Word-level matching is
# required to avoid the Arabic root collision between "ادمج" (imperative:
# "merge it", a USER_DIRECTIVE) and "مدموج"/"دمج" (reported state: "is
# merged"/"merge"[noun]) -- both share the root د-م-ج as a substring but are
# different words and different claim types.
_QUESTION_WORDS = {"هل"}
_QUESTION_MARKERS = ("؟", "?")
_PROPOSAL_WORDS = {"اقترح", "أقترح", "اقتراح", "propose", "suggest", "proposal"}
_CORRECTION_WORDS = {
    "خطأ",
    "تصحيح",
    "صحح",
    "غلط",
    "wrong",
    "incorrect",
    "correction",
    "mistake",
}
_REPORTED_STATE_WORDS = {
    "مدموج",
    "دمج",
    "دُمج",
    "مغلق",
    "أُغلق",
    "اغلق",
    "اكتمل",
    "انتهى",
    "تم",
    "merged",
    "closed",
    "done",
    "completed",
    "deployed",
    "نُشر",
    "نشر",
}

_WORD_SPLIT_RE = re.compile(r"[\s،.,؛;:!]+")


def _tokenize(normalized_text: str) -> list[str]:
    return [tok for tok in _WORD_SPLIT_RE.split(normalized_text) if tok]


def _classify_claim_type(normalized_text: str) -> str:
    """Deterministic, word-level claim-type classification. Order matters:
    a question about a reported state ("هل تم الدمج؟") is still fundamentally
    a QUESTION (asking, not asserting), so QUESTION is checked first."""
    if any(marker in normalized_text for marker in _QUESTION_MARKERS):
        return CLAIM_TYPE_QUESTION
    tokens = set(_tokenize(normalized_text))
    tokens_lower = {t.lower() for t in tokens}
    if tokens & _QUESTION_WORDS:
        return CLAIM_TYPE_QUESTION
    if tokens & _CORRECTION_WORDS or tokens_lower & _CORRECTION_WORDS:
        return CLAIM_TYPE_CORRECTION
    if tokens & _REPORTED_STATE_WORDS or tokens_lower & _REPORTED_STATE_WORDS:
        return CLAIM_TYPE_REPORTED_STATE
    if tokens & _PROPOSAL_WORDS or tokens_lower & _PROPOSAL_WORDS:
        return CLAIM_TYPE_PROPOSAL
    return CLAIM_TYPE_USER_DIRECTIVE


def normalize(text: str) -> str:
    return unicodedata.normalize("NFKC", text)


@dataclasses.dataclass(frozen=True, kw_only=True)
class ConversationDirective:
    raw_text: str
    normalized_text: str
    intent: str
    claim_type: str
    verification_required: bool
    confidence_class: str
    produced_by: str = "conversation_intelligence"

    def __post_init__(self) -> None:
        if self.normalized_text != normalize(self.raw_text):
            raise AgentContractError(
                "normalized_text must equal unicodedata.normalize('NFKC', raw_text)."
            )
        if self.claim_type not in ALLOWED_CLAIM_TYPES:
            raise AgentContractError(f"Unknown claim_type {self.claim_type!r}.")
        expected_verification, expected_confidence = _CLAIM_TYPE_SEMANTICS[
            self.claim_type
        ]
        if self.verification_required != expected_verification:
            raise AgentContractError(
                f"claim_type={self.claim_type!r} requires "
                f"verification_required={expected_verification!r}; a "
                "REPORTED_STATE or CORRECTION claim can never be marked as "
                "not requiring verification -- that would let a reported "
                "claim silently become trusted state."
            )
        if self.confidence_class != expected_confidence:
            raise AgentContractError(
                f"claim_type={self.claim_type!r} requires "
                f"confidence_class={expected_confidence!r}, got "
                f"{self.confidence_class!r}."
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
        claim_type = _classify_claim_type(normalized)
        verification_required, confidence_class = _CLAIM_TYPE_SEMANTICS[claim_type]
        return ConversationDirective(
            raw_text=raw_text,
            normalized_text=normalized,
            intent=intent,
            claim_type=claim_type,
            verification_required=verification_required,
            confidence_class=confidence_class,
        )
