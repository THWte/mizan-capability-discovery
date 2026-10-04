"""
MIZAN PaddleOCR Sandbox - Cold Start vs Warm Processing Benchmark

Separates model/engine initialization ("cold start") from steady-state
document conversion ("warm processing"), per the A4 requirement that the
earlier combined measurement be corrected. Compares at least:

- born-digital PDF / OCR still applied (no OCR-off path for this engine --
  see adapter.py module docstring)
- scanned PDF / OCR applied

Writes results to benchmark/cold_warm_results.json. Run manually (not part
of the default pytest collection, since it is a measurement script, not a
pass/fail test) via:

    .venv\\Scripts\\python.exe benchmark\\benchmark_cold_warm.py
"""
from __future__ import annotations

import json
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from adapter import PaddleOcrAdapter  # noqa: E402

FIXTURES = ROOT / "fixtures"

try:
    import psutil

    _PROCESS = psutil.Process()

    def rss_mb() -> float:
        return _PROCESS.memory_info().rss / (1024 * 1024)

    HAVE_PSUTIL = True
except ImportError:
    def rss_mb() -> float:
        return -1.0

    HAVE_PSUTIL = False


def main() -> None:
    results: dict = {"have_psutil": HAVE_PSUTIL}

    # Build the synthetic born-digital fixture BEFORE constructing the
    # adapter. During investigation for this benchmark, constructing the
    # fixture AFTER adapter construction reproduced the Windows native access
    # violation (see RESULTS.md Windows Stability section) twice in a row;
    # building it first avoided the crash in follow-up repro runs. This
    # ordering is not asserted as a fix -- it is one more UNRESOLVED,
    # order-sensitive data point, recorded honestly rather than hidden.
    import tempfile

    from reportlab.pdfgen import canvas as rl_canvas

    tmp_dir = pathlib.Path(tempfile.mkdtemp())
    born_digital_pdf = tmp_dir / "born_digital_benchmark.pdf"
    c = rl_canvas.Canvas(str(born_digital_pdf), pagesize=(612, 792))
    for i in range(40):
        c.drawString(72, 740 - i * 15, f"Benchmark born-digital text line {i}.")
    c.showPage()
    c.save()

    rss_before_init = rss_mb()
    t0 = time.monotonic()
    adapter = PaddleOcrAdapter()
    cold_start_elapsed = time.monotonic() - t0
    rss_after_init = rss_mb()

    results["cold_start"] = {
        "description": "PaddleOcrAdapter() construction: version check + PaddleOCR pipeline init "
        "(model weights already cached locally from earlier sandbox runs -- this measures "
        "load time, not network download time; see test_offline_local_first.py for the "
        "offline/no-network scenario).",
        "elapsed_seconds": cold_start_elapsed,
        "rss_mb_before": rss_before_init,
        "rss_mb_after": rss_after_init,
        "rss_delta_mb": (rss_after_init - rss_before_init) if HAVE_PSUTIL else None,
    }

    def warm_runs(label: str, fixture_name: str, n: int = 3) -> list[dict]:
        runs = []
        for i in range(n):
            t0 = time.monotonic()
            result = adapter.convert(FIXTURES / fixture_name)
            elapsed = time.monotonic() - t0
            runs.append({
                "run": i + 1,
                "elapsed_seconds": elapsed,
                "success": result.success,
                "ocr_mode": result.ocr_mode,
                "ocr_applied": result.ocr_applied,
            })
            print(f"{label} run {i + 1}: {elapsed:.2f}s (success={result.success})")
        return runs

    # "born-digital" fixture was already synthesized above, before adapter
    # construction (see note above). NOTE: per the Windows Access Violation
    # Investigation (see RESULTS.md / test_vector_pdf_capability.py), running
    # a vector-text PDF conversion together with other conversions in one
    # process carries a documented, intermittent native-crash risk. This
    # benchmark accepts that risk as part of measuring the born-digital warm
    # path, and the risk itself is exactly the kind of production-relevant
    # workload this benchmark is measuring the cost of -- it is not hidden.
    results["warm_born_digital_ocr_applied"] = None  # overwritten below
    runs = []
    for i in range(3):
        t0 = time.monotonic()
        result = adapter.convert(born_digital_pdf)
        elapsed = time.monotonic() - t0
        runs.append({
            "run": i + 1, "elapsed_seconds": elapsed, "success": result.success,
            "ocr_mode": result.ocr_mode, "ocr_applied": result.ocr_applied,
        })
        print(f"born_digital run {i + 1}: {elapsed:.2f}s (success={result.success})")
    results["warm_born_digital_ocr_applied"] = runs

    results["warm_scanned_ocr_applied"] = warm_runs("scanned", "scanned_arabic_clear.pdf", n=3)

    rss_final = rss_mb()
    results["rss_mb_final"] = rss_final

    out_path = ROOT / "benchmark" / "cold_warm_results.json"
    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote {out_path}")
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
