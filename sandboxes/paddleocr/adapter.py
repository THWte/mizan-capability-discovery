"""
MIZAN PaddleOCR Adapter (Sandbox Prototype)

Purpose
-------
Isolate PaddleOCR behind an internal interface so MIZAN never depends on
PaddleOCR's API directly. If PaddleOCR is replaced, abandoned, or swapped for
another engine, only this adapter module needs to change.

This module intentionally mirrors the shape of
`sandboxes/docling/adapter.py`'s `NormalizedDocumentResult` contract (same
field names/semantics where applicable) so the two engines can be compared
on equal terms by the same downstream bridge/test methodology -- but this
file has NO import-time or runtime dependency on Docling or anything in
`sandboxes/docling/`.

Separation of concerns (MIZAN methodology)
-------------------------------------------
    SOURCE -> RAW EXTRACTION -> NORMALIZATION -> INTERPRETATION -> VERIFICATION -> ACCEPTED FACT
              \\___________________________/
                   this adapter's scope

`raw_text` is exactly what PaddleOCR returned, concatenated in its own
detection order, unmodified. `normalized_text` is `raw_text` after Unicode
NFKC normalization and is what downstream MIZAN processing should read.
Neither is an accepted fact.

Structural capability difference from Docling (recorded here, not hidden)
---------------------------------------------------------------------------
PaddleOCR (the OCR-only pipeline used by this adapter) has NO text-layer
reader: it always rasterizes every page and always runs OCR, even for a
born-digital PDF with a perfect existing text layer. This adapter still
runs the same pypdf-based born/scanned/ambiguous pre-check used by the
Docling adapter so the classification is recorded for comparison, but
`ocr_applied` is unconditionally True for every PDF -- there is no
OCR-off fast path. This is an architecturally different capability than
Docling's conditional OCR routing, not a bug in this adapter.

Table structure
---------------
This adapter uses PaddleOCR's plain OCR pipeline (`PaddleOCR(...)`), which
returns a flat, ordered list of recognized text lines with bounding boxes --
it does NOT perform table/cell/row/column structure detection. PaddleOCR
separately ships a layout+table pipeline (`PPStructureV3`) that was NOT
evaluated in this sandbox (different model footprint and scope). Tables are
therefore always reported as raw OCR line output with `tables=[]`, and table
*structure* accuracy is explicitly `NOT AVAILABLE` for this adapter -- see
`benchmark/RESULTS.md`.

Version pinning (real capability-discovery finding)
----------------------------------------------------
`paddleocr==3.3.3` + `paddlepaddle==3.2.2` are REQUIRED. Newer combinations
(`paddleocr==3.7.0` + `paddlepaddle==3.3.1`, the versions pip installs by
default as of this sandbox) crash or raise on this machine:

- `paddlepaddle==3.3.1`: raises
  `NotImplementedError: (Unimplemented) ConvertPirAttribute2RuntimeAttribute
  not support [pir::ArrayAttribute<pir::DoubleAttribute>]` inside oneDNN's
  text-detection runtime, for every PDF, every language, every model variant
  tried (server/mobile det). Confirmed as a known upstream regression
  (PaddlePaddle PIR + oneDNN attribute conversion bug affecting
  PaddleOCR 3.5+ / PaddlePaddle 3.3+ on CPU).
- `paddlepaddle==3.0.0`: crashes the Python process with a native Windows
  access violation (exit code -1073741819 / 0xC0000005) during the same
  text-detection call -- not a catchable Python exception at all.
- `paddlepaddle==2.6.2`: raises `AttributeError:
  'AnalysisConfig' object has no attribute 'set_optimization_level'` at
  predictor construction -- `paddleocr==3.3.3`'s pipeline framework
  (`paddlex`) requires a newer Paddle inference API than 2.6.2 exposes.

Only `paddleocr==3.3.3` + `paddlepaddle==3.2.2` produced correct Arabic OCR
output without crashing, across all fixtures tested in this sandbox.
"""
from __future__ import annotations

import dataclasses
import hashlib
import pathlib
import time
import traceback
import unicodedata
from typing import Optional

MIN_CHARS_PER_PAGE_BORN_DIGITAL = 40

REQUIRED_PADDLEOCR_VERSION = "3.3.3"
REQUIRED_PADDLEPADDLE_VERSION = "3.2.2"


@dataclasses.dataclass
class TableResult:
    """Always empty for this adapter -- see module docstring "Table structure"."""
    rows: list[list[str]]
    page_or_slide: Optional[int] = None
    caption: Optional[str] = None


@dataclasses.dataclass
class SectionResult:
    """One OCR-detected text line, preserving PaddleOCR's own reading order.
    `level` is always 0 (PaddleOCR's plain OCR pipeline has no heading/layout
    classification -- see module docstring)."""
    level: int
    text: str
    page_number: Optional[int] = None
    bbox: Optional[tuple[float, float, float, float]] = None
    """(x0, y0, x1, y1) axis-aligned bounding box in source-image pixel
    coordinates, when PaddleOCR provided one. Used for structure/order
    verification, never for identity."""
    confidence: Optional[float] = None
    """PaddleOCR's own per-line recognition confidence (0..1), when
    available. This is an engine confidence score, NOT a MIZAN verification
    signal -- see Observation-boundary tests."""


@dataclasses.dataclass
class Provenance:
    """Enough information to trace extracted content back to its source file.

    `source_sha256` is mandatory (same rule as the Docling adapter, same
    MIZAN Provenance Contract GATE). Computed from file bytes before any
    PaddleOCR call runs, so it is available even if OCR itself fails.
    """
    source_path: str
    source_file_name: str
    source_size_bytes: int
    source_sha256: str
    engine: str
    engine_version: str
    model: str
    model_version: Optional[str]
    """PaddleOCR does not expose a single semantic version string per model
    file (only a model *name*, e.g. 'arabic_PP-OCRv5_mobile_rec'). When no
    true version is available, this is explicitly None, not a guessed or
    fabricated value -- see Provenance adversarial tests."""


@dataclasses.dataclass
class NormalizedDocumentResult:
    """The unified output contract between PaddleOCR and MIZAN. Mirrors
    `sandboxes/docling/adapter.NormalizedDocumentResult` field-for-field
    where the capability is comparable, so the same bridge/test methodology
    can target either engine's output. See module docstring for the fields
    that differ in meaning for this engine (`tables` always empty,
    `ocr_applied` always True for PDFs)."""
    success: bool
    file_type: str

    raw_text: str
    normalized_text: str

    sections: list[SectionResult]
    tables: list[TableResult]
    metadata: dict
    warnings: list[str]
    errors: list[str]
    provenance: Provenance
    processing_time_seconds: float

    ocr_mode: str
    """Pre-check classification only (informational) -- see module
    docstring "Structural capability difference from Docling". One of:
    'born_digital', 'scanned', 'ambiguous', 'not_applicable', 'unknown'."""

    ocr_reason: str
    ocr_engine: str
    ocr_applied: bool
    """True whenever PaddleOCR actually ran on this file (always True for
    PDFs processed successfully by this adapter; False only for failures
    before OCR was attempted, e.g. missing file)."""


class PaddleOcrAdapterError(Exception):
    """Raised only for adapter-level failures that are not simple per-file errors."""


def sha256_of_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_text(raw_text: str) -> str:
    """Apply the MIZAN-mandated NFKC normalization step. Applied uniformly
    regardless of whether this specific engine is observed to need it for a
    given input -- normalization must not be conditional on the engine."""
    return unicodedata.normalize("NFKC", raw_text)


def _classify_pdf_for_ocr(path: pathlib.Path) -> tuple[str, str]:
    """Same pypdf-based heuristic as the Docling adapter, reused verbatim for
    cross-engine comparability. Purely informational for this adapter (see
    module docstring) -- it does NOT turn OCR off."""
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        page_count = max(len(reader.pages), 1)
        text = "".join((page.extract_text() or "") for page in reader.pages)
        non_ws_chars = len("".join(text.split()))
        chars_per_page = non_ws_chars / page_count

        if non_ws_chars == 0:
            return "scanned", f"No extractable text layer found across {page_count} page(s)."
        if chars_per_page >= MIN_CHARS_PER_PAGE_BORN_DIGITAL:
            return (
                "born_digital",
                f"Text layer found: ~{chars_per_page:.0f} non-whitespace chars/page "
                f"(>= threshold {MIN_CHARS_PER_PAGE_BORN_DIGITAL}). NOTE: this adapter still "
                f"runs OCR regardless -- see 'ocr_applied'.",
            )
        return (
            "ambiguous",
            f"Sparse text layer found: ~{chars_per_page:.0f} non-whitespace chars/page "
            f"(< threshold {MIN_CHARS_PER_PAGE_BORN_DIGITAL}).",
        )
    except Exception as exc:  # noqa: BLE001
        return "unknown", f"OCR routing pre-check failed ({type(exc).__name__}: {exc})."


class PaddleOcrAdapter:
    """Thin wrapper around PaddleOCR's plain OCR pipeline, with mandatory
    NFKC normalization and MIZAN-shaped provenance/output.

    MIZAN components should depend on this class (or an equivalent
    interface), never on `paddleocr` directly.
    """

    def __init__(self, lang: str = "ar") -> None:
        # Imported lazily so importing this module doesn't require
        # PaddleOCR's heavy ML dependencies unless an adapter instance is
        # actually constructed.
        import paddleocr
        import paddle

        installed_paddleocr = getattr(paddleocr, "__version__", "unknown")
        installed_paddle = getattr(paddle, "__version__", "unknown")
        if installed_paddleocr != REQUIRED_PADDLEOCR_VERSION or installed_paddle != REQUIRED_PADDLEPADDLE_VERSION:
            raise PaddleOcrAdapterError(
                "Unsupported PaddleOCR/PaddlePaddle version combination for this adapter: "
                f"paddleocr=={installed_paddleocr}, paddlepaddle=={installed_paddle}. "
                f"Required: paddleocr=={REQUIRED_PADDLEOCR_VERSION}, "
                f"paddlepaddle=={REQUIRED_PADDLEPADDLE_VERSION}. See module docstring "
                "'Version pinning' for the specific crashes other combinations produce."
            )

        self._engine_version = installed_paddleocr
        self._paddle_version = installed_paddle
        self._lang = lang
        self._ocr = paddleocr.PaddleOCR(
            lang=lang,
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
        )
        # PaddleOCR names its detector/recognizer models but does not expose
        # a semantic version per model (see Provenance.model_version
        # docstring) -- record the model *names* actually used.
        self._model_name = f"text_det+arabic_rec(lang={lang})"

    def convert(self, path: str | pathlib.Path) -> NormalizedDocumentResult:
        path = pathlib.Path(path)
        start = time.monotonic()
        warnings: list[str] = []
        errors: list[str] = []

        file_size = path.stat().st_size if path.exists() else 0
        file_sha256 = sha256_of_file(path) if path.exists() else ""
        provenance = Provenance(
            source_path=str(path),
            source_file_name=path.name,
            source_size_bytes=file_size,
            source_sha256=file_sha256,
            engine="paddleocr",
            engine_version=self._engine_version,
            model=self._model_name,
            model_version=None,
        )

        if not path.exists():
            errors.append(f"File does not exist: {path}")
            return self._failure_result(path, provenance, errors, start, "not_applicable", "File missing.", "none", False)

        ocr_mode, ocr_reason = ("not_applicable", "Non-PDF format; pre-check only defined for PDF.")
        if path.suffix.lower() == ".pdf":
            ocr_mode, ocr_reason = _classify_pdf_for_ocr(path)

        try:
            pages = list(self._ocr.predict(str(path)))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{type(exc).__name__}: {exc}")
            errors.append(traceback.format_exc(limit=3))
            return self._failure_result(
                path, provenance, errors, start, ocr_mode, ocr_reason,
                f"paddleocr(lang={self._lang})", False, warnings,
            )

        try:
            sections: list[SectionResult] = []
            raw_lines: list[str] = []
            for page in pages:
                page_index = page.get("page_index")
                page_number = (page_index + 1) if isinstance(page_index, int) else None
                rec_texts = page.get("rec_texts") or []
                rec_scores = page.get("rec_scores") or []
                rec_boxes = page.get("rec_boxes")
                for i, text in enumerate(rec_texts):
                    if not text:
                        continue
                    raw_lines.append(text)
                    score = float(rec_scores[i]) if i < len(rec_scores) else None
                    bbox = None
                    if rec_boxes is not None and i < len(rec_boxes):
                        try:
                            x0, y0, x1, y1 = (float(v) for v in rec_boxes[i])
                            bbox = (x0, y0, x1, y1)
                        except Exception:  # noqa: BLE001
                            bbox = None
                    sections.append(SectionResult(
                        level=0, text=text, page_number=page_number, bbox=bbox, confidence=score,
                    ))

            if not raw_lines:
                warnings.append("PaddleOCR returned zero recognized text lines for this document.")

            raw_text = "\n".join(raw_lines)
            normalized_text = normalize_text(raw_text)

            metadata = {
                "page_count": len(pages),
                "lang": self._lang,
                "paddle_version": self._paddle_version,
            }

            elapsed = time.monotonic() - start
            return NormalizedDocumentResult(
                success=True,
                file_type=path.suffix.lstrip(".").lower(),
                raw_text=raw_text,
                normalized_text=normalized_text,
                sections=sections,
                tables=[],  # see module docstring "Table structure"
                metadata=metadata,
                warnings=warnings,
                errors=errors,
                provenance=provenance,
                processing_time_seconds=elapsed,
                ocr_mode=ocr_mode,
                ocr_reason=ocr_reason,
                ocr_engine=f"paddleocr(lang={self._lang})",
                ocr_applied=True,
            )
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Post-processing failure: {type(exc).__name__}: {exc}")
            return self._failure_result(
                path, provenance, errors, start, ocr_mode, ocr_reason,
                f"paddleocr(lang={self._lang})", True, warnings,
            )

    @staticmethod
    def _failure_result(
        path: pathlib.Path,
        provenance: Provenance,
        errors: list[str],
        start: float,
        ocr_mode: str,
        ocr_reason: str,
        ocr_engine: str,
        ocr_applied: bool,
        warnings: Optional[list[str]] = None,
    ) -> NormalizedDocumentResult:
        return NormalizedDocumentResult(
            success=False,
            file_type=path.suffix.lstrip(".").lower(),
            raw_text="",
            normalized_text="",
            sections=[],
            tables=[],
            metadata={},
            warnings=warnings or [],
            errors=errors,
            provenance=provenance,
            processing_time_seconds=time.monotonic() - start,
            ocr_mode=ocr_mode,
            ocr_reason=ocr_reason,
            ocr_engine=ocr_engine,
            ocr_applied=ocr_applied,
        )
