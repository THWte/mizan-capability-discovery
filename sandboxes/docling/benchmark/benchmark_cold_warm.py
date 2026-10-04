"""
MIZAN Docling Sandbox - Cold Start vs Warm Run Benchmark

Separates two phases that the original benchmark conflated:

- COLD START: constructing DoclingAdapter() for the first time in a fresh
  process. This includes Docling pipeline initialization and, if models are
  not already cached on disk, model download. (In this environment models
  were already cached from earlier sandbox runs, so this measures
  initialization/load time, not network download time -- see
  offline/local-first findings below for why that distinction matters.)
- WARM PROCESSING: repeated document conversions using an already-constructed
  adapter, with models already loaded in memory.

Run with:

    .venv\\Scripts\\python.exe benchmark\\benchmark_cold_warm.py

Writes a JSON report to benchmark/cold_warm_results.json and prints a summary
table. Optionally reports CPU/RAM via `psutil` if installed; otherwise notes
that CPU/RAM could not be measured reliably in this environment.
"""
from __future__ import annotations

import json
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

FIXTURES = ROOT / "fixtures"
WARM_REPEATS = 3

try:
    import psutil

    _PROCESS = psutil.Process()
    HAVE_PSUTIL = True
except ImportError:
    _PROCESS = None
    HAVE_PSUTIL = False


def _mem_mb() -> float | None:
    if not HAVE_PSUTIL:
        return None
    return _PROCESS.memory_info().rss / (1024 * 1024)


def _cpu_times() -> dict | None:
    if not HAVE_PSUTIL:
        return None
    t = _PROCESS.cpu_times()
    return {"user": t.user, "system": t.system}


def main() -> None:
    report: dict = {
        "psutil_available": HAVE_PSUTIL,
        "cold_start": {},
        "warm_processing": {},
    }

    # --- Cold start ---------------------------------------------------
    mem_before = _mem_mb()
    cpu_before = _cpu_times()
    t0 = time.monotonic()
    from adapter import DoclingAdapter  # import here so it's inside the timing window

    adapter = DoclingAdapter()
    cold_elapsed = time.monotonic() - t0
    mem_after = _mem_mb()
    cpu_after = _cpu_times()

    report["cold_start"] = {
        "description": "DoclingAdapter() construction (pipeline init; model "
        "load from cache since models were pre-cached in this environment).",
        "elapsed_seconds": cold_elapsed,
        "rss_mb_before": mem_before,
        "rss_mb_after": mem_after,
        "rss_delta_mb": (mem_after - mem_before) if HAVE_PSUTIL else None,
        "cpu_times_before": cpu_before,
        "cpu_times_after": cpu_after,
    }
    print(f"[cold start] adapter construction: {cold_elapsed:.2f}s "
          f"(psutil={'yes' if HAVE_PSUTIL else 'no'})")

    # --- Warm processing: born-digital / OCR OFF -----------------------
    warm_born_digital = []
    for i in range(WARM_REPEATS):
        t0 = time.monotonic()
        result = adapter.convert(FIXTURES / "sample_plain_text.pdf")
        elapsed = time.monotonic() - t0
        warm_born_digital.append(elapsed)
        print(f"[warm] born_digital run {i}: {elapsed:.2f}s (ocr_mode={result.ocr_mode})")

    # --- Warm processing: scanned / OCR ON ------------------------------
    warm_scanned = []
    for i in range(WARM_REPEATS):
        t0 = time.monotonic()
        result = adapter.convert(FIXTURES / "scanned_arabic_clear.pdf")
        elapsed = time.monotonic() - t0
        warm_scanned.append(elapsed)
        print(f"[warm] scanned run {i}: {elapsed:.2f}s (ocr_mode={result.ocr_mode})")

    report["warm_processing"] = {
        "born_digital_ocr_off": {
            "fixture": "sample_plain_text.pdf",
            "runs_seconds": warm_born_digital,
            "mean_seconds": sum(warm_born_digital) / len(warm_born_digital),
        },
        "scanned_ocr_on": {
            "fixture": "scanned_arabic_clear.pdf",
            "runs_seconds": warm_scanned,
            "mean_seconds": sum(warm_scanned) / len(warm_scanned),
        },
        "rss_mb_after_all_runs": _mem_mb(),
    }

    out_path = ROOT / "benchmark" / "cold_warm_results.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nWritten: {out_path}")
    print("\n--- Summary ---")
    print(f"Cold start (adapter construction):      {cold_elapsed:.2f}s")
    print(f"Warm born-digital/OCR-off mean:          {report['warm_processing']['born_digital_ocr_off']['mean_seconds']:.2f}s")
    print(f"Warm scanned/OCR-on mean:                {report['warm_processing']['scanned_ocr_on']['mean_seconds']:.2f}s")
    if not HAVE_PSUTIL:
        print("CPU/RAM: psutil not installed -- not measured. (pip install psutil to enable)")


if __name__ == "__main__":
    main()
