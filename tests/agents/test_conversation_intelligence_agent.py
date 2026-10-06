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
    reject, or promote anything -- only raw_text/normalized_text/intent/
    produced_by exist."""
    agent = ConversationIntelligenceAgent()
    directive = agent.interpret("review this")
    field_names = {f.name for f in __import__("dataclasses").fields(directive)}
    assert field_names == {"raw_text", "normalized_text", "intent", "produced_by"}
