"""High-level upload service that stores files and triggers ingestion."""

import uuid
from pathlib import Path

from backend.config import get_settings
from backend.database import SessionLocal
from backend.ingestion.common import IngestedDocument, get_ingester
from backend.models import Document

# Supported extensions -> canonical file_type
_EXTENSION_MAP: dict[str, str] = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".doc": "doc",
    ".xlsx": "xlsx",
    ".xls": "xls",
    ".csv": "csv",
}


def _file_type_from_filename(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    file_type = _EXTENSION_MAP.get(ext)
    if file_type is None:
        supported = ", ".join(sorted(_EXTENSION_MAP.keys()))
        raise ValueError(
            f"Unsupported file extension: {ext!r}. Supported: {supported}"
        )
    return file_type


def _store_file(filename: str, file_content: bytes) -> tuple[Path, str, str]:
    """Write file to disk and return (dest_path, storage_path, file_type)."""
    file_type = _file_type_from_filename(filename)
    unique_prefix = uuid.uuid4().hex[:12]
    safe_name = f"{unique_prefix}_{filename}"
    originals_dir = get_settings().originals_dir
    dest_path = originals_dir / safe_name
    dest_path.write_bytes(file_content)
    storage_path = str(dest_path.relative_to(originals_dir.parent.parent))
    return dest_path, storage_path, file_type


def store_and_ingest(
    filename: str, file_content: bytes
) -> tuple[Document, IngestedDocument]:
    """Store an uploaded file to disk, create a DB record, and ingest it."""
    dest_path, storage_path, file_type = _store_file(filename, file_content)

    ingester = get_ingester(file_type)
    ingested = ingester.ingest(dest_path, storage_path)

    db = SessionLocal()
    try:
        doc = Document(
            original_filename=filename,
            storage_path=storage_path,
            file_type=file_type,
            page_count=ingested.page_count,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        db.expunge(doc)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    return doc, ingested


def store_and_ingest_csv_rows(
    filename: str, file_content: bytes
) -> list[tuple[Document, IngestedDocument]]:
    """Store a CSV file and create one Document per data row."""
    dest_path, storage_path, _file_type = _store_file(filename, file_content)

    from backend.ingestion.csv_ingester import CsvIngester
    ingester = CsvIngester()
    ingested_docs = ingester.ingest_rows(dest_path, storage_path, original_filename=filename)

    results: list[tuple[Document, IngestedDocument]] = []
    db = SessionLocal()
    try:
        for ingested in ingested_docs:
            doc = Document(
                original_filename=ingested.original_filename,
                storage_path=storage_path,
                file_type="csv",
                page_count=1,
                source_text=ingested.text,
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)
            db.expunge(doc)
            results.append((doc, ingested))
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    return results
