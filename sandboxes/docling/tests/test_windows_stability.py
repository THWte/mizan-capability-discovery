"""
MIZAN Docling Sandbox - Windows Access Violation Investigation

A `Windows fatal exception: access violation` message has been observed
printed (via Python's faulthandler, from a background thread) during pytest
runs that use Docling's OCR/PDF-parsing pipeline on this machine. It has not
caused a visible pytest test FAILURE, but it DOES change the host process's
exit code in at least one observed run, and it is a native-code fault --
exactly the kind of issue that must not be waved away as "Low" just because
no assertion failed.

This module does NOT claim to fix or fully explain the fault. Its purpose is
to:
1. Attempt to reproduce it under repeated / sequential / bounded-concurrent
   load.
2. Record occurrence counts and any effect on test outcomes.
3. Record what evidence IS available (stack trace lines, which native module
   is implicated).
4. Classify honestly, including UNRESOLVED where root cause can't be nailed
   down from inside pytest alone.

Known evidence so far (from an actual captured run in this sandbox, not a
hypothesis):

    Windows fatal exception: access violation
    Thread 0x... (most recent call first):
      File ".../docling_parse/pdf_parser.py", line ??? in
        get_connected_shape_bounding_boxes

This implicates `docling_parse` (Docling's native PDF parsing backend, a
C++ extension), NOT RapidOCR or PyTorch directly, based on the one stack
trace captured to date. It appeared only after the full test session had
already completed and reported results (visible after the last collected
test's PASSED line), consistent with a fault during interpreter/thread
teardown rather than during an individual conversion call. This sandbox
cannot access the native extension's internals, so it CANNOT rule out
PyTorch/RapidOCR involvement in other runs -- only report what was observed.
"""
from __future__ import annotations

import concurrent.futures
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from adapter import DoclingAdapter  # noqa: E402

FIXTURES = ROOT / "fixtures"

REPEATED_RUNS = 5
SEQUENTIAL_DOCS = [
    "sample_plain_text.pdf",
    "sample_with_tables.pdf",
    "sample_arabic.pdf",
    "scanned_arabic_clear.pdf",
]
BOUNDED_CONCURRENCY = 2  # deliberately small; this is a probe, not a stress test.


@pytest.fixture(scope="module")
def adapter() -> DoclingAdapter:
    return DoclingAdapter()


def test_repeated_sequential_runs_same_document_do_not_corrupt_results(adapter):
    """
    Runs the SAME document through the adapter REPEATED_RUNS times,
    sequentially, in-process. Records whether every run succeeds and whether
    results stay identical. Does not assert anything about the native-level
    access violation message itself (pytest cannot reliably observe it as a
    Python-level exception since it does not raise one here) -- only that
    the adapter's own success/consistency guarantees hold across repetition.
    """
    results = []
    for i in range(REPEATED_RUNS):
        result = adapter.convert(FIXTURES / "sample_plain_text.pdf")
        results.append(result)
        assert result.success is True, f"Run {i}: conversion failed: {result.errors}"

    first_text = results[0].normalized_text
    for i, r in enumerate(results[1:], start=1):
        assert r.normalized_text == first_text, (
            f"Run {i} produced different output than run 0 -- possible instability."
        )


def test_sequential_runs_across_multiple_different_documents(adapter):
    """Runs several DIFFERENT documents sequentially (covers born-digital,
    table, Arabic, and scanned/OCR paths in one sequence) to probe whether
    switching code paths back-to-back triggers instability."""
    outcomes = []
    for name in SEQUENTIAL_DOCS:
        result = adapter.convert(FIXTURES / name)
        outcomes.append((name, result.success, len(result.errors)))

    failed = [o for o in outcomes if not o[1]]
    assert failed == [], f"Unexpected failures during sequential multi-document run: {failed}"


def test_bounded_concurrent_runs_do_not_crash_the_process(adapter):
    """
    Runs a small, bounded number of conversions CONCURRENTLY using a thread
    pool (Docling's own pipeline is itself multi-threaded internally, which is
    the likely source of the access-violation signal, so this specifically
    probes additional concurrency on top of that). Bounded to
    BOUNDED_CONCURRENCY=2 workers deliberately -- this is a probe to see if
    concurrency changes the failure signature, not a production concurrency
    recommendation.
    """
    docs = [FIXTURES / "sample_plain_text.pdf", FIXTURES / "sample_arabic.pdf"]

    with concurrent.futures.ThreadPoolExecutor(max_workers=BOUNDED_CONCURRENCY) as pool:
        futures = [pool.submit(adapter.convert, doc) for doc in docs]
        results = [f.result(timeout=120) for f in futures]

    assert all(r.success for r in results), (
        "One or more concurrent conversions failed: "
        f"{[(r.provenance.source_file_name, r.errors) for r in results if not r.success]}"
    )


# ---------------------------------------------------------------------------
# Documented finding (not an executable assertion -- see module docstring and
# benchmark/RESULTS.md "Windows Access Violation Investigation" section for
# the full writeup, evidence, and classification).
# ---------------------------------------------------------------------------

def test_investigation_finding_is_documented():
    """
    This test does not reproduce or detect the fault itself (it cannot --
    the fault is a native-level signal printed by Python's faulthandler, not
    a catchable Python exception, and it was observed to occur AFTER pytest's
    own reporting completed in the one run where it was captured). It exists
    only to assert that the investigation's findings are written down in
    benchmark/RESULTS.md where a human reviewer will see them, since an
    un-reproducible native fault must not be silently dropped.
    """
    results_md = (ROOT / "benchmark" / "RESULTS.md").read_text(encoding="utf-8")
    assert "Windows Access Violation" in results_md
    assert "UNRESOLVED" in results_md or "docling_parse" in results_md
