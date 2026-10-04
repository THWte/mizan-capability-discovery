"""
MIZAN Docling Adapter (Sandbox Prototype)

Purpose
-------
Isolate Docling behind an internal interface so MIZAN never depends on Docling's
API directly. If Docling is replaced, abandoned, or swapped for another engine,
only this adapter module needs to change.

Separation of concerns (MIZAN methodology)
-------------------------------------------
This adapter produces EXTRACTED CONTENT only. It never produces an "accepted fact".
The pipeline is:

    SOURCE -> EXTRACTED CONTENT (this adapter) -> INTERPRETATION -> VERIFICATION -> ACCEPTED FACT

Everything returned by `convert()` is raw, unverified extraction and must be treated
as provisional by any downstream MIZAN component.
"""
from __future__ import annotations

import dataclasses
import pathlib
import time
import traceback
from typing import Optional


@dataclasses.dataclass
class TableResult:
    """A single extracted table, in row-major form."""
    rows: list[list[str]]
    page_or_slide: Optional[int] = None
    caption: Optional[str] = None


@dataclasses.dataclass
class SectionResult:
    """A heading/paragraph unit, preserving document order."""
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

    IMPORTANT: `full_text`, `sections`, and `tables` are EXTRACTED CONTENT, not
    verified facts. MIZAN's interpretation/verification layers must process this
    before anything here is treated as an accepted fact about a case.
    """
    success: bool
    file_type: str
    full_text: str
    sections: list[SectionResult]
    tables: list[TableResult]
    metadata: dict
    warnings: list[str]
    errors: list[str]
    provenance: Provenance
    processing_time_seconds: float


class DoclingAdapterError(Exception):
    """Raised only for adapter-level failures that are not simple per-file errors."""


class DoclingAdapter:
    """
    Thin wrapper around Docling's DocumentConverter.

    MIZAN components should depend on this class (or an equivalent interface), never
    on `docling` directly.
    """

    def __init__(self) -> None:
        # Imported lazily so that importing this module doesn't require Docling's
        # heavy ML dependencies unless an adapter instance is actually constructed.
        from docling.document_converter import DocumentConverter
        import docling

        self._converter = DocumentConverter()
        self._engine_version = getattr(docling, "__version__", "unknown")

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
            return self._failure_result(path, provenance, errors, start)

        try:
            result = self._converter.convert(str(path))
        except Exception as exc:  # Docling raises various exceptions per-backend.
            errors.append(f"{type(exc).__name__}: {exc}")
            errors.append(traceback.format_exc(limit=3))
            return self._failure_result(path, provenance, errors, start)

        try:
            doc = result.document
            full_text = doc.export_to_markdown()

            sections: list[SectionResult] = []
            for item, _level in doc.iterate_items():
                label = getattr(item, "label", None)
                text = getattr(item, "text", None)
                if text is None:
                    continue
                label_name = getattr(label, "value", str(label)) if label else "text"
                heading_level = 1 if "section_header" in label_name or "title" in label_name else 0
                sections.append(SectionResult(level=heading_level, text=text))

            tables: list[TableResult] = []
            for table_item in getattr(doc, "tables", []):
                try:
                    df = table_item.export_to_dataframe()
                    rows = [list(df.columns.astype(str))] + df.astype(str).values.tolist()
                    tables.append(TableResult(rows=rows))
                except Exception as table_exc:  # noqa: BLE001
                    warnings.append(f"Table extraction partially failed: {table_exc}")

            metadata = {
                "page_count": getattr(doc, "num_pages", lambda: None)()
                if callable(getattr(doc, "num_pages", None))
                else getattr(doc, "num_pages", None),
                "name": getattr(doc, "name", None),
            }

            elapsed = time.monotonic() - start
            return NormalizedDocumentResult(
                success=True,
                file_type=path.suffix.lstrip(".").lower(),
                full_text=full_text,
                sections=sections,
                tables=tables,
                metadata=metadata,
                warnings=warnings,
                errors=errors,
                provenance=provenance,
                processing_time_seconds=elapsed,
            )
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Post-processing failure: {type(exc).__name__}: {exc}")
            return self._failure_result(path, provenance, errors, start)

    @staticmethod
    def _failure_result(
        path: pathlib.Path,
        provenance: Provenance,
        errors: list[str],
        start: float,
    ) -> NormalizedDocumentResult:
        return NormalizedDocumentResult(
            success=False,
            file_type=path.suffix.lstrip(".").lower(),
            full_text="",
            sections=[],
            tables=[],
            metadata={},
            warnings=[],
            errors=errors,
            provenance=provenance,
            processing_time_seconds=time.monotonic() - start,
        )
