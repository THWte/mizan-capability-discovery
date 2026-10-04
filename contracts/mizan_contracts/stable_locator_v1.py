"""
MIZAN Stable Locator Contract v1

Implements docs/architecture/ARCHITECTURAL_INVARIANTS.md Invariant 3
(MIZAN Owns Identity and Stable Locators).

A Stable Locator is MIZAN's own durable address for a document, page,
block, or span. It is built and validated entirely from MIZAN-issued
sequence numbers -- never from an external engine's internal ID, a database
row ID, or a retrieval-system ID.

Hierarchy
---------
    MIZAN-DOC-000001
    |-- PAGE-000001
        |-- BLOCK-000001
            |-- SPAN-000001

Encoded as a single '/'-joined path so that hierarchy consistency (AC-09)
is structurally checkable: a SPAN locator's path literally contains its
parent BLOCK, PAGE, and DOCUMENT locators as prefixes.

No module in this file may import, reference, or depend on any third-party
document-intelligence or retrieval engine (Docling, PaddleOCR, MinerU,
Qdrant, pgvector, or any other).
"""
from __future__ import annotations

import re

from .errors import ContractValidationError

CONTRACT_VERSION = "v1"

_DOC_RE = re.compile(r"^MIZAN-DOC-(\d{6})$")
_PAGE_RE = re.compile(r"^PAGE-(\d{6})$")
_BLOCK_RE = re.compile(r"^BLOCK-(\d{6})$")
_SPAN_RE = re.compile(r"^SPAN-(\d{6})$")

# Identifiers belonging to external engines/systems that must never be
# accepted as, or embedded verbatim into, a MIZAN stable locator (AC-08).
_BANNED_ENGINE_ID_PATTERNS = (
    re.compile(r"docling", re.IGNORECASE),
    re.compile(r"mineru", re.IGNORECASE),
    re.compile(r"qdrant", re.IGNORECASE),
    re.compile(r"pgvector", re.IGNORECASE),
    re.compile(r"paddleocr", re.IGNORECASE),
    re.compile(r"database_row_id", re.IGNORECASE),
    re.compile(r"^row[_-]?\d+$", re.IGNORECASE),
)


def _seq(n: int) -> str:
    if n < 1:
        raise ContractValidationError("Locator sequence numbers must be >= 1.")
    return f"{n:06d}"


def build_document_locator(sequence: int) -> str:
    """Build a MIZAN-owned document locator, e.g. 'MIZAN-DOC-000001'.

    Takes only a MIZAN-internal sequence number -- no engine input of any
    kind is accepted by this function's signature, which is itself part of
    the AC-07 guarantee (MIZAN can create a locator with zero external
    engine state).
    """
    return f"MIZAN-DOC-{_seq(sequence)}"


def build_page_locator(document_locator: str, page_sequence: int) -> str:
    validate_locator_component(document_locator, "document")
    return f"{document_locator}/{'PAGE-' + _seq(page_sequence)}"


def build_block_locator(page_locator: str, block_sequence: int) -> str:
    validate_locator_component(page_locator, "page")
    return f"{page_locator}/{'BLOCK-' + _seq(block_sequence)}"


def build_span_locator(block_locator: str, span_sequence: int) -> str:
    validate_locator_component(block_locator, "block")
    return f"{block_locator}/{'SPAN-' + _seq(span_sequence)}"


def validate_locator_component(locator: str, expected_kind: str) -> None:
    """Validate that `locator` is a well-formed MIZAN locator of `expected_kind`
    ('document' | 'page' | 'block' | 'span'), and reject any embedded
    external-engine identifier (AC-08).
    """
    if not isinstance(locator, str) or not locator:
        raise ContractValidationError("Locator must be a non-empty string.")

    for pattern in _BANNED_ENGINE_ID_PATTERNS:
        if pattern.search(locator):
            raise ContractValidationError(
                f"Locator {locator!r} contains an external engine identifier "
                "pattern and cannot be used as a MIZAN stable locator. "
                "Stable locators are MIZAN-owned only (Invariant 3)."
            )

    segments = locator.split("/")
    kind_terminal = {
        "document": (1, _DOC_RE),
        "page": (2, _PAGE_RE),
        "block": (3, _BLOCK_RE),
        "span": (4, _SPAN_RE),
    }
    expected_len, terminal_re = kind_terminal[expected_kind]
    if len(segments) != expected_len:
        raise ContractValidationError(
            f"Locator {locator!r} does not have the expected depth for "
            f"kind={expected_kind!r} (expected {expected_len} segment(s), "
            f"found {len(segments)})."
        )
    if not _DOC_RE.match(segments[0]):
        raise ContractValidationError(f"Locator {locator!r} has an invalid document segment.")
    if expected_len >= 2 and not _PAGE_RE.match(segments[1]):
        raise ContractValidationError(f"Locator {locator!r} has an invalid page segment.")
    if expected_len >= 3 and not _BLOCK_RE.match(segments[2]):
        raise ContractValidationError(f"Locator {locator!r} has an invalid block segment.")
    if expected_len >= 4 and not _SPAN_RE.match(segments[3]):
        raise ContractValidationError(f"Locator {locator!r} has an invalid span segment.")
    if not terminal_re.match(segments[-1]):
        raise ContractValidationError(
            f"Locator {locator!r} terminal segment does not match expected kind {expected_kind!r}."
        )


def validate_hierarchy_consistency(
    document_locator: str,
    page_locator: str | None = None,
    block_locator: str | None = None,
    span_locator: str | None = None,
) -> None:
    """Validate that page/block/span locators, if given, are structurally
    rooted in `document_locator` (and each other) in order (AC-09).

    Raises ContractValidationError if a span claims a block/page/document
    chain that is inconsistent with its own literal path.
    """
    validate_locator_component(document_locator, "document")

    if page_locator is not None:
        validate_locator_component(page_locator, "page")
        if not page_locator.startswith(document_locator + "/"):
            raise ContractValidationError(
                f"page_locator {page_locator!r} is not rooted in document_locator {document_locator!r}."
            )

    if block_locator is not None:
        if page_locator is None:
            raise ContractValidationError("block_locator given without a page_locator.")
        validate_locator_component(block_locator, "block")
        if not block_locator.startswith(page_locator + "/"):
            raise ContractValidationError(
                f"block_locator {block_locator!r} is not rooted in page_locator {page_locator!r}."
            )

    if span_locator is not None:
        if block_locator is None:
            raise ContractValidationError("span_locator given without a block_locator.")
        validate_locator_component(span_locator, "span")
        if not span_locator.startswith(block_locator + "/"):
            raise ContractValidationError(
                f"span_locator {span_locator!r} is not rooted in block_locator {block_locator!r}."
            )


def is_external_engine_identifier(value: str) -> bool:
    """Return True if `value` matches a known external-engine ID pattern.
    Used directly by AC-08 tests and by any future adapter wiring to reject
    such values before they could ever reach a locator field.
    """
    return any(pattern.search(value) for pattern in _BANNED_ENGINE_ID_PATTERNS)
