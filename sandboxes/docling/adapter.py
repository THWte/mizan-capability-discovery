"""
MIZAN Docling Adapter (Sandbox Prototype)

Purpose
-------
Isolate Docling behind an internal interface so MIZAN never depends on Docling's
API directly. If Docling is replaced, abandoned, or swapped for another engine,
only this adapter module needs to change.

Separation of concerns (MIZAN methodology)
-------------------------------------------
This adapter sits strictly at the first two stages of MIZAN's evidence pipeline:

    SOURCE -> RAW EXTRACTION -> NORMALIZATION -> INTERPRETATION -> VERIFICATION -> ACCEPTED FACT
              \\___________________________/
                   this adapter's scope

Nothing produced here is an "accepted fact". `raw_text` is exactly what Docling
emitted (kept for provenance/audit). `normalized_text` is `raw_text` after
Unicode NFKC normalization and is the text downstream components should read for
further processing. Neither field, nor any other field on
`NormalizedDocumentResult`, may be treated as verified by this adapter -- that is
the responsibility of MIZAN's interpretation/verification layers, which do not
exist in this sandbox.

OCR routing
-----------
Docling's default `DocumentConverter()` runs OCR on every PDF page regardless of
whether a text layer already exists, which is unnecessarily slow for born-digital
PDFs (see benchmark/RESULTS.md). This adapter instead inspects each PDF with
`pypdf` first and classifies it as one of:

- "born_digital": a usable text layer was found -> OCR is turned OFF.
- "scanned": no usable text layer was found -> OCR is turned ON.
- "ambiguous": a text layer exists but is too sparse to trust -> OCR is turned ON
  as a safe fallback, and a warning is attached to the result so a human/MIZAN
  reviewer is aware the document needs attention.

The routing decision is recorded in the result's `ocr_mode`, `ocr_reason`, and
`ocr_engine` fields -- not just described in documentation.
"""
from __future__ import annotations

import dataclasses
import pathlib
import time
import traceback
import unicodedata
from typing import Optional

# Below this many non-whitespace characters per page (averaged), a PDF's text
# layer is considered too sparse to trust and is routed to "ambiguous".
MIN_CHARS_PER_PAGE_BORN_DIGITAL = 40


@dataclasses.dataclass
class TableResult:
    """A single extracted table, in row-major form. Raw extraction only."""
    rows: list[list[str]]
    page_or_slide: Optional[int] = None
    caption: Optional[str] = None


@dataclasses.dataclass
class SectionResult:
    """A heading/paragraph unit, preserving document order. Raw extraction only."""
    level: int  # 0 = body paragraph, 1+ = heading level
    text: str


@dataclasses.dataclass
class Provenance:
    """Enough information to trace extracted content back to its source file."""
    source_path: str
    source_file_name: str
    source_size_bytes: int
    engine: str
    engine_version: str


@dataclasses.dataclass
class NormalizedDocumentResult:
    """
    The unified output contract between Docling (or any future engine) and MIZAN.

    IMPORTANT: every field here is RAW EXTRACTION or NORMALIZATION output, never
    an accepted fact. MIZAN's interpretation/verification layers must process this
    before anything here is treated as verified knowledge about a case.
    """
    success: bool
    file_type: str

    raw_text: str
    """Exactly what Docling returned, unmodified. Kept for provenance/audit."""

    normalized_text: str
    """`raw_text` after Unicode NFKC normalization. This is what downstream
    MIZAN processing should read -- see benchmark/RESULTS.md for why raw text
    alone is not safe to use for Arabic content."""

    sections: list[SectionResult]
    tables: list[TableResult]
    metadata: dict
    warnings: list[str]
    errors: list[str]
    provenance: Provenance
    processing_time_seconds: float

    ocr_mode: str
    """One of: 'born_digital' (OCR off), 'scanned' (OCR on), 'ambiguous'
    (OCR on, safe fallback), 'not_applicable' (non-PDF format), or 'unknown'
    (routing pre-check itself failed, OCR forced on as a safe default)."""

    ocr_reason: str
    """Human-readable reason for the ocr_mode decision, e.g. measured
    characters-per-page from the pre-check."""

    ocr_engine: str
    """Which OCR engine was active for this conversion, or 'none' if OCR was
    not used."""


class DoclingAdapterError(Exception):
    """Raised only for adapter-level failures that are not simple per-file errors."""


def normalize_text(raw_text: str) -> str:
    """Apply the MIZAN-mandated NFKC normalization step. See
    benchmark/RESULTS.md for the measured defect this corrects: Docling's PDF
    text extraction can return Arabic in Unicode Presentation Forms (e.g. the
    glyph for "that": looks like separate presentation-form codepoints) rather
    than plain Arabic letters. NFKC recovers the original letters without
    altering word order."""
    return unicodedata.normalize("NFKC", raw_text)


def _classify_pdf_for_ocr(path: pathlib.Path) -> tuple[str, str]:
    """
    Inspect a PDF's existing text layer (if any) using pypdf, independent of
    Docling, to decide whether OCR is needed. Returns (ocr_mode, reason).

    This is a deliberately simple, auditable heuristic, not a model. It exists
    so the OCR decision is explicit and testable rather than "whatever Docling
    does by default".
    """
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
                f"(>= threshold {MIN_CHARS_PER_PAGE_BORN_DIGITAL}).",
            )
        return (
            "ambiguous",
            f"Sparse text layer found: ~{chars_per_page:.0f} non-whitespace chars/page "
            f"(< threshold {MIN_CHARS_PER_PAGE_BORN_DIGITAL}). Routing to OCR as a safe "
            f"fallback; this document should be reviewed manually.",
        )
    except Exception as exc:  # noqa: BLE001
        return (
            "unknown",
            f"OCR routing pre-check failed ({type(exc).__name__}: {exc}); defaulting to OCR ON.",
        )


class DoclingAdapter:
    """
    Thin wrapper around Docling's DocumentConverter, with explicit OCR routing
    and mandatory NFKC normalization.

    MIZAN components should depend on this class (or an equivalent interface),
    never on `docling` directly.
    """

    def __init__(self) -> None:
        # Imported lazily so that importing this module doesn't require Docling's
        # heavy ML dependencies unless an adapter instance is actually constructed.
        import docling
        from docling.document_converter import DocumentConverter, PdfFormatOption
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        from docling.datamodel.base_models import InputFormat

        from docling.datamodel.pipeline_options import RapidOcrOptions

        self._InputFormat = InputFormat
        self._engine_version = getattr(docling, "__version__", "unknown")

        ocr_off_opts = PdfPipelineOptions()
        ocr_off_opts.do_ocr = False

        # CRITICAL FINDING (see benchmark/RESULTS.md "OCR language configuration"):
        # Docling's default RapidOcrOptions() uses lang=['ch'] (Chinese), which
        # silently fails on Arabic script -- it does not error, it just produces
        # garbage or drops Arabic text entirely. An explicit RapidOcrOptions(
        # lang=['arabic']) is REQUIRED for Arabic OCR to work at all. This was
        # discovered empirically in this sandbox, not documented upstream in an
        # obvious place, and is exactly the kind of silent-failure risk this
        # adapter exists to surface rather than hide.
        ocr_on_opts = PdfPipelineOptions()
        ocr_on_opts.do_ocr = True
        ocr_on_opts.ocr_options = RapidOcrOptions(lang=["arabic", "en"])

        # Two pre-built converters: one with OCR forced off (fast path for
        # born-digital PDFs), one with OCR forced on (scanned/ambiguous path),
        # configured for Arabic+English recognition since that is MIZAN's
        # target language mix.
        self._converter_ocr_off = DocumentConverter(
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=ocr_off_opts)}
        )
        self._converter_ocr_on = DocumentConverter(
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=ocr_on_opts)}
        )
        # Default converter for non-PDF formats (OCR routing not applicable).
        self._converter_default = DocumentConverter()

    def convert(self, path: str | pathlib.Path) -> NormalizedDocumentResult:
        path = pathlib.Path(path)
        start = time.monotonic()
        warnings: list[str] = []
        errors: list[str] = []

        file_size = path.stat().st_size if path.exists() else 0
        provenance = Provenance(
            source_path=str(path),
            source_file_name=path.name,
            source_size_bytes=file_size,
            engine="docling",
            engine_version=self._engine_version,
        )

        if not path.exists():
            errors.append(f"File does not exist: {path}")
            return self._failure_result(path, provenance, errors, start, "not_applicable", "File missing.", "none")

        is_pdf = path.suffix.lower() == ".pdf"
        ocr_mode = "not_applicable"
        ocr_reason = "Non-PDF format; OCR routing does not apply."
        ocr_engine = "none"
        converter = self._converter_default

        if is_pdf:
            ocr_mode, ocr_reason = _classify_pdf_for_ocr(path)
            if ocr_mode == "born_digital":
                converter = self._converter_ocr_off
                ocr_engine = "none"
            elif ocr_mode in ("scanned", "ambiguous", "unknown"):
                converter = self._converter_ocr_on
                ocr_engine = "rapidocr(lang=arabic,en)"
                if ocr_mode == "ambiguous":
                    warnings.append("AMBIGUOUS PDF: " + ocr_reason + " Manual review recommended.")
                elif ocr_mode == "unknown":
                    warnings.append("OCR ROUTING UNCERTAIN: " + ocr_reason)

        try:
            result = converter.convert(str(path))
        except Exception as exc:  # Docling raises various exceptions per-backend.
            errors.append(f"{type(exc).__name__}: {exc}")
            errors.append(traceback.format_exc(limit=3))
            return self._failure_result(path, provenance, errors, start, ocr_mode, ocr_reason, ocr_engine, warnings)

        try:
            doc = result.document
            raw_text = doc.export_to_markdown()
            normalized_text = normalize_text(raw_text)

            sections: list[SectionResult] = []
            for item, _level in doc.iterate_items():
                label = getattr(item, "label", None)
                text = getattr(item, "text", None)
                if text is None:
                    continue
                label_name = getattr(label, "value", str(label)) if label else "text"
                heading_level = 1 if ("section_header" in label_name or "title" in label_name) else 0
                sections.append(SectionResult(level=heading_level, text=text))

            tables: list[TableResult] = []
            for table_item in getattr(doc, "tables", []):
                try:
                    df = table_item.export_to_dataframe(doc)
                    rows = [list(df.columns.astype(str))] + df.astype(str).values.tolist()
                    tables.append(TableResult(rows=rows))
                except Exception as table_exc:  # noqa: BLE001
                    warnings.append(f"Table extraction partially failed: {table_exc}")

            num_pages_attr = getattr(doc, "num_pages", None)
            page_count = num_pages_attr() if callable(num_pages_attr) else num_pages_attr
            metadata = {
                "page_count": page_count,
                "name": getattr(doc, "name", None),
            }

            elapsed = time.monotonic() - start
            return NormalizedDocumentResult(
                success=True,
                file_type=path.suffix.lstrip(".").lower(),
                raw_text=raw_text,
                normalized_text=normalized_text,
                sections=sections,
                tables=tables,
                metadata=metadata,
                warnings=warnings,
                errors=errors,
                provenance=provenance,
                processing_time_seconds=elapsed,
                ocr_mode=ocr_mode,
                ocr_reason=ocr_reason,
                ocr_engine=ocr_engine,
            )
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Post-processing failure: {type(exc).__name__}: {exc}")
            return self._failure_result(path, provenance, errors, start, ocr_mode, ocr_reason, ocr_engine, warnings)

    @staticmethod
    def _failure_result(
        path: pathlib.Path,
        provenance: Provenance,
        errors: list[str],
        start: float,
        ocr_mode: str,
        ocr_reason: str,
        ocr_engine: str,
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
        )
