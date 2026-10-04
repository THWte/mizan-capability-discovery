"""AC-09: Hierarchical locator validation.

A Span cannot be considered consistent with a Document/Page/Block chain
that its own literal path does not match.
"""
import pytest

from mizan_contracts import stable_locator_v1
from mizan_contracts.errors import ContractValidationError


def _build_consistent_chain():
    document_locator = stable_locator_v1.build_document_locator(1)
    page_locator = stable_locator_v1.build_page_locator(document_locator, 1)
    block_locator = stable_locator_v1.build_block_locator(page_locator, 1)
    span_locator = stable_locator_v1.build_span_locator(block_locator, 1)
    return document_locator, page_locator, block_locator, span_locator


def test_consistent_hierarchy_is_accepted():
    document_locator, page_locator, block_locator, span_locator = _build_consistent_chain()
    # Must not raise.
    stable_locator_v1.validate_hierarchy_consistency(
        document_locator, page_locator, block_locator, span_locator
    )


def test_span_from_a_different_document_is_rejected():
    _, page_locator, block_locator, span_locator = _build_consistent_chain()
    other_document_locator = stable_locator_v1.build_document_locator(2)
    with pytest.raises(ContractValidationError):
        stable_locator_v1.validate_hierarchy_consistency(
            other_document_locator, page_locator, block_locator, span_locator
        )


def test_span_from_a_different_page_is_rejected():
    document_locator, _, block_locator, span_locator = _build_consistent_chain()
    other_page_locator = stable_locator_v1.build_page_locator(document_locator, 2)
    with pytest.raises(ContractValidationError):
        stable_locator_v1.validate_hierarchy_consistency(
            document_locator, other_page_locator, block_locator, span_locator
        )


def test_block_without_a_page_is_rejected():
    document_locator, _, block_locator, _ = _build_consistent_chain()
    with pytest.raises(ContractValidationError):
        stable_locator_v1.validate_hierarchy_consistency(
            document_locator, page_locator=None, block_locator=block_locator
        )


def test_span_without_a_block_is_rejected():
    document_locator, page_locator, _, span_locator = _build_consistent_chain()
    with pytest.raises(ContractValidationError):
        stable_locator_v1.validate_hierarchy_consistency(
            document_locator, page_locator=page_locator, block_locator=None, span_locator=span_locator
        )
