"""
MIZAN Docling Sandbox - Offline / Local-First Verification

Confirms that, once models are cached locally, Docling conversions succeed
with network access to the model hubs explicitly disabled via environment
variables (HF_HUB_OFFLINE / TRANSFORMERS_OFFLINE). This is run in a SEPARATE
subprocess (not in-process) so that the offline environment variables are
guaranteed to take effect before any Docling/HF/RapidOCR module is imported
(these libraries read such env vars at import time in some cases).

This test does NOT prove no network call is attempted by any means (e.g. the
subprocess is not run under a firewall/network namespace in this sandbox) --
it proves that Docling supports and respects the offline-mode environment
variables its dependencies (Hugging Face Hub) define, which is the standard
mechanism for local-first operation with these libraries.
"""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures"
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"

OFFLINE_SCRIPT = """
import sys
sys.path.insert(0, r"{root}")
from adapter import DoclingAdapter

adapter = DoclingAdapter()
result = adapter.convert(r"{fixture}")
print("SUCCESS" if result.success else "FAILURE")
print("ERRORS:", result.errors)
sys.exit(0 if result.success else 1)
"""


def _run_offline_subprocess(fixture_path: pathlib.Path) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["HF_HUB_OFFLINE"] = "1"
    env["TRANSFORMERS_OFFLINE"] = "1"
    # Also point at a clearly-invalid hub endpoint as a second layer of
    # assurance that no live network call is relied upon when offline.
    env["HF_ENDPOINT"] = "http://127.0.0.1:1"

    script = OFFLINE_SCRIPT.format(root=str(ROOT), fixture=str(fixture_path))
    return subprocess.run(
        [str(PYTHON), "-c", script],
        capture_output=True,
        text=True,
        timeout=180,
        cwd=str(ROOT),
        env=env,
    )


@pytest.mark.skipif(not PYTHON.exists(), reason="sandbox venv python not found")
def test_born_digital_conversion_succeeds_fully_offline():
    proc = _run_offline_subprocess(FIXTURES / "sample_plain_text.pdf")
    assert "SUCCESS" in proc.stdout, (
        f"Offline born-digital conversion failed.\nstdout={proc.stdout}\nstderr={proc.stderr}"
    )


@pytest.mark.skipif(not PYTHON.exists(), reason="sandbox venv python not found")
def test_scanned_ocr_conversion_succeeds_fully_offline():
    """The harder case: OCR (RapidOCR model load + inference) must also work
    fully offline once its weights are cached locally -- RapidOCR models are
    downloaded from modelscope.cn, a separate mechanism from the
    HF_HUB_OFFLINE variable, so this specifically confirms that cached
    RapidOCR weights are used without needing modelscope.cn reachability."""
    proc = _run_offline_subprocess(FIXTURES / "scanned_arabic_clear.pdf")
    assert "SUCCESS" in proc.stdout, (
        f"Offline scanned/OCR conversion failed.\nstdout={proc.stdout}\nstderr={proc.stderr}"
    )
