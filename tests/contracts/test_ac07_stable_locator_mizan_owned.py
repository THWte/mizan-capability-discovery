"""AC-07: MIZAN can create and verify a Stable Locator without any external
engine ID.
"""
from mizan_contracts import stable_locator_v1


def test_mizan_builds_full_locator_hierarchy_from_pure_sequence_numbers():
    # Every builder function's signature accepts only MIZAN-internal
    # sequence integers (and parent locator strings it built itself) --
    # there is no parameter anywhere for an engine ID of any kind.
    document_locator = stable_locator_v1.build_document_locator(1)
    page_locator = stable_locator_v1.build_page_locator(document_locator, 1)
    block_locator = stable_locator_v1.build_block_locator(page_locator, 1)
    span_locator = stable_locator_v1.build_span_locator(block_locator, 1)

    assert document_locator == "MIZAN-DOC-000001"
    assert page_locator == "MIZAN-DOC-000001/PAGE-000001"
    assert block_locator == "MIZAN-DOC-000001/PAGE-000001/BLOCK-000001"
    assert span_locator == "MIZAN-DOC-000001/PAGE-000001/BLOCK-000001/SPAN-000001"

    # And MIZAN can independently verify each one, again with no engine
    # state involved.
    stable_locator_v1.validate_locator_component(document_locator, "document")
    stable_locator_v1.validate_locator_component(page_locator, "page")
    stable_locator_v1.validate_locator_component(block_locator, "block")
    stable_locator_v1.validate_locator_component(span_locator, "span")


def test_locator_builder_functions_accept_no_engine_parameter():
    import inspect

    for builder in (
        stable_locator_v1.build_document_locator,
        stable_locator_v1.build_page_locator,
        stable_locator_v1.build_block_locator,
        stable_locator_v1.build_span_locator,
    ):
        params = inspect.signature(builder).parameters
        for name in params:
            assert "engine" not in name.lower(), (
                f"{builder.__name__} must not accept an engine-related parameter ({name!r})."
            )
