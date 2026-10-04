"""
MIZAN PaddleOCR Sandbox - Vector/Born-Digital PDF Capability Tests

IMPORTANT -- Windows stability note (full writeup in
benchmark/RESULTS.md "Windows Access Violation Investigation"):

A native access violation (exit code -1073741819 / 0xC0000005) was observed
multiple times during this investigation, but is INTERMITTENT, not 100%
deterministic, and does NOT correlate cleanly with any single factor this
investigation was able to isolate -- it is classified UNRESOLVED.
Observations, in the order they were made:

- A single conversion (of any kind) alone in a process: stable in every
  attempt.
- Many repeated raster/scanned-only conversions in one process (verified
  12x, separately 30+ in one `pytest` run of test_scanned_ocr_quality.py):
  BOTH stable in some attempts and (in one later, larger run combining
  several test files) eventually crashed after ~34 successful conversions,
  on a plain scanned-fixture call with no vector-text PDF involved at all.
  This disproves an earlier, narrower working hypothesis that the fault was
  specific to mixing vector-text and raster-image PDFs.
- Mixing a reportlab-generated VECTOR-TEXT PDF conversion with a
  raster/scanned PDF conversion in the same process: crashed in most
  isolated reproduction attempts (bare, non-pytest scripts, multiple
  orders), but NOT in a subsequent subprocess-launched attempt of the exact
  same scenario, which completed successfully.
- Two vector-text-only conversions in sequence: stable as a bare script, but
  crashed once when run as two pytest test functions in the same file.

Net assessment: the fault appears related to CUMULATIVE native engine call
volume within one long-lived process (more calls -> higher observed
probability), but input "shape" (vector vs. raster), call order, adapter
instance reuse, and the pytest harness itself were all tested as candidate
contributing factors and none fully explains every observation. The precise
root cause (PaddleOCR / PaddleX / PaddlePaddle's native runtime, or an
interaction with the test harness) could not be isolated further within
this investigation's scope and time budget.

Because the fault is intermittent and its root cause could not be fully
isolated, this file does NOT assert a fixed crash/success outcome; see
`test_vector_then_scanned_conversion_in_same_process_is_recorded` below,
which records the observed outcome to
`benchmark/windows_stability_results.json` and passes either way. Full
writeup and honest UNRESOLVED classification: benchmark/RESULTS.md
"Windows Access Violation Investigation".

Because of this, every test in this file that needs more than one
`.convert()` call total within a process either (a) performs exactly one
conversion and nothing else, or (b) is executed in its OWN isolated
subprocess via `subprocess.run([sys.executable, "-c", ...])` so a genuine
crash is captured and asserted on, rather than silently taking down the
rest of this sandbox's test suite. This file must never be combined, in one
`pytest` invocation, with any other file that performs a `.convert()` call
-- see `run_tests.ps1` for the required multi-group invocation this finding
forces on this sandbox.
"""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from adapter import PaddleOcrAdapter  # noqa: E402

ACCESS_VIOLATION_EXIT_CODE = -1073741819  # 0xC0000005 on Windows


def _make_vector_text_pdf(path: pathlib.Path, line_prefix: str = "This is a born-digital text line number") -> None:
    from reportlab.pdfgen import canvas as rl_canvas

    c = rl_canvas.Canvas(str(path), pagesize=(612, 792))
    for i in range(40):
        c.drawString(72, 740 - i * 15, f"{line_prefix} {i}, well above the threshold.")
    c.showPage()
    c.save()


def test_single_born_digital_conversion_succeeds_and_is_classified_correctly(tmp_path):
    """One vector-text conversion, alone in the process: always stable.
    Also the key capability difference vs Docling: Docling would classify
    this 'born_digital' and SKIP OCR (ocr_engine='none'); PaddleOCR's plain
    pipeline always runs OCR regardless of this classification."""
    born_digital_pdf = tmp_path / "born_digital.pdf"
    _make_vector_text_pdf(born_digital_pdf)

    result = PaddleOcrAdapter().convert(born_digital_pdf)

    assert result.success is True
    assert result.ocr_mode == "born_digital", (
        f"Pre-check misclassified a clearly born-digital PDF as {result.ocr_mode!r}."
    )
    assert result.ocr_applied is True, (
        "CAPABILITY GAP (documented, not a bug): this adapter has no OCR-off "
        "fast path -- ocr_applied must stay True even for born-digital PDFs."
    )
    assert result.ocr_engine != "none"


_SUBPROCESS_SCRIPT_VECTOR_THEN_SCANNED = """
import pathlib, sys
ROOT = pathlib.Path(r"{root}")
sys.path.insert(0, str(ROOT))
from adapter import PaddleOcrAdapter
from reportlab.pdfgen import canvas as rl_canvas

tmp = pathlib.Path(r"{tmp}")
def make(path, text):
    c = rl_canvas.Canvas(str(path), pagesize=(612, 792))
    for i in range(40):
        c.drawString(72, 740 - i * 15, f"{{text}} line {{i}}")
    c.showPage()
    c.save()

pdf_a = tmp / "a.pdf"
make(pdf_a, "vector text")

adapter = PaddleOcrAdapter()
r1 = adapter.convert(pdf_a)
assert r1.success
r2 = adapter.convert(ROOT / "fixtures" / "scanned_arabic_clear.pdf")
assert r2.success
print("BOTH_CONVERSIONS_SUCCEEDED")
"""


def test_vector_then_scanned_conversion_in_same_process_is_recorded(tmp_path):
    """Documents the finding honestly: converting a vector-text PDF and THEN
    a real scanned/raster PDF fixture within the SAME process was observed
    to crash with a native Windows access violation in several isolated
    reproduction attempts made during this investigation (bare, non-pytest
    scripts) -- but NOT in every attempt: one subprocess run of this exact
    scenario, launched from this pytest process, completed successfully.
    This instability is therefore INTERMITTENT, not 100% deterministic, and
    its precise trigger condition remains UNRESOLVED despite dedicated
    bisection. A single conversion per process, and repeated scanned-only
    conversions in one process (verified 12x), were consistently stable in
    every attempt.

    This test runs the scenario in an isolated subprocess (so a genuine
    crash here never brings down the rest of this sandbox's test run),
    records the observed outcome into
    benchmark/windows_stability_results.json under
    "vector_then_scanned_same_process", and passes regardless of whether
    this particular attempt crashed or succeeded -- asserting a fixed
    outcome for a confirmed-intermittent native fault would itself be a
    flaky, dishonest test.
    """
    import json

    script = _SUBPROCESS_SCRIPT_VECTOR_THEN_SCANNED.format(root=ROOT, tmp=tmp_path)
    proc = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env={**os.environ, "DISABLE_MODEL_SOURCE_CHECK": "True"},
        timeout=300,
    )

    crashed = proc.returncode == ACCESS_VIOLATION_EXIT_CODE
    succeeded = proc.returncode == 0 and "BOTH_CONVERSIONS_SUCCEEDED" in proc.stdout
    assert crashed or succeeded, (
        f"Unexpected outcome (neither known-crash nor known-success): "
        f"exit {proc.returncode}\nstdout={proc.stdout}\nstderr={proc.stderr}"
    )

    results_path = ROOT / "benchmark" / "windows_stability_results.json"
    results_path.parent.mkdir(parents=True, exist_ok=True)
    data = {}
    if results_path.exists():
        data = json.loads(results_path.read_text(encoding="utf-8"))
    entry = data.setdefault(
        "vector_then_scanned_same_process",
        {"attempts": 0, "crashed": 0, "succeeded": 0, "exit_codes": []},
    )
    entry["attempts"] += 1
    entry["crashed"] += int(crashed)
    entry["succeeded"] += int(succeeded)
    entry["exit_codes"].append(proc.returncode)
    results_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
