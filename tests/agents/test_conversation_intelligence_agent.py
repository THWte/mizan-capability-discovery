"""Tests for the MIZAN Agent Society v1 Conversation Intelligence Agent."""
import pytest

from mizan_agents.conversation_intelligence import ConversationIntelligenceAgent
from mizan_agents.errors import AgentContractError


def test_arabic_review_intent_classified():
    agent = ConversationIntelligenceAgent()
    directive = agent.interpret("راجع هذا الـ PR من فضلك")
    assert directive.intent == "architecture_review"


def test_english_implement_intent_classified():
    agent = ConversationIntelligenceAgent()
    directive = agent.interpret("Please implement this change now")
    assert directive.intent == "implementation"


def test_unclassified_intent_for_unknown_text():
    agent = ConversationIntelligenceAgent()
    directive = agent.interpret("what time is it")
    assert directive.intent == "unclassified"


def test_empty_text_rejected():
    agent = ConversationIntelligenceAgent()
    with pytest.raises(AgentContractError):
        agent.interpret("   ")


def test_raw_text_preserved_separately_from_normalized_text():
    agent = ConversationIntelligenceAgent()
    # Arabic-Indic digits + presentation forms normalize under NFKC.
    raw = "\uFEE5\uFEE2\uFEDF\uFE94"  # Arabic presentation-form sequence
    directive = agent.interpret(raw)
    assert directive.raw_text == raw
    # The real guarantee: normalized_text is *exactly* NFKC(raw_text), not
    # independently supplied.
    import unicodedata

    assert directive.normalized_text == unicodedata.normalize("NFKC", raw)


def test_produced_by_is_fixed_agent_name():
    agent = ConversationIntelligenceAgent()
    directive = agent.interpret("merge this")
    assert directive.produced_by == "conversation_intelligence"


def test_directive_has_no_approval_authority_fields():
    """This agent's output type carries no field that could let it approve,
    reject, or promote anything -- only observation/classification fields
    exist, never an approval/acceptance/fact field."""
    agent = ConversationIntelligenceAgent()
    directive = agent.interpret("review this")
    field_names = {f.name for f in __import__("dataclasses").fields(directive)}
    assert field_names == {
        "raw_text",
        "normalized_text",
        "intent",
        "claim_type",
        "verification_required",
        "confidence_class",
        "produced_by",
    }


def test_reported_merge_state_classified_as_reported_state_requiring_verification():
    """PART 17 worked example: 'PR #7 مدموج' (PR #7 is merged) is a report
    about the world, not an instruction -- it must never be silently
    trusted as fact without verification."""
    agent = ConversationIntelligenceAgent()
    directive = agent.interpret("PR #7 مدموج")
    assert directive.claim_type == "REPORTED_STATE"
    assert directive.verification_required is True
    assert directive.confidence_class == "UNVERIFIED_REPORTED_STATE"


def test_reported_state_in_english_also_classified_correctly():
    agent = ConversationIntelligenceAgent()
    directive = agent.interpret("PR #7 is merged")
    assert directive.claim_type == "REPORTED_STATE"
    assert directive.verification_required is True


def test_imperative_merge_instruction_is_user_directive_not_reported_state():
    """The Arabic root collision case: 'ادمج' (imperative 'merge it') must
    not be misclassified as a REPORTED_STATE merely because it shares a
    root with 'مدموج' (reported 'is merged')."""
    agent = ConversationIntelligenceAgent()
    directive = agent.interpret("ادمج PR رقم 7")
    assert directive.claim_type == "USER_DIRECTIVE"
    assert directive.verification_required is False


def test_question_classified_as_question_not_reported_state():
    agent = ConversationIntelligenceAgent()
    directive = agent.interpret("هل تم دمج PR رقم 7؟")
    assert directive.claim_type == "QUESTION"
    assert directive.verification_required is False


def test_proposal_classified_separately():
    agent = ConversationIntelligenceAgent()
    directive = agent.interpret("أقترح أن نستخدم فرعًا جديدًا")
    assert directive.claim_type == "PROPOSAL"
    assert directive.verification_required is False


def test_correction_claim_requires_verification():
    agent = ConversationIntelligenceAgent()
    directive = agent.interpret("هذا خطأ، التقرير السابق غير صحيح")
    assert directive.claim_type == "CORRECTION"
    assert directive.verification_required is True


def test_reported_state_cannot_be_constructed_without_verification_required():
    """Structural enforcement: even a hand-constructed ConversationDirective
    cannot claim REPORTED_STATE while disabling verification_required."""
    from mizan_agents.conversation_intelligence import ConversationDirective

    with pytest.raises(AgentContractError):
        ConversationDirective(
            raw_text="PR #7 مدموج",
            normalized_text="PR #7 مدموج",
            intent="unclassified",
            claim_type="REPORTED_STATE",
            verification_required=False,
            confidence_class="UNVERIFIED_REPORTED_STATE",
        )
