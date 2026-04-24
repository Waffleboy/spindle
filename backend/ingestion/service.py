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
    """Determine the canonical file type from a filename's extension.

    Raises:
        ValueError: If the extension is not supported.
    """
    ext = Path(filename).suffix.lower()
    file_type = _EXTENSION_MAP.get(ext)
    if file_type is None:
        supported = ", ".join(sorted(_EXTENSION_MAP.keys()))
        raise ValueError(
            f"Unsupported file extension: {ext!r}. Supported: {supported}"
        )
    return file_type


def store_and_ingest(
    filename: str, file_content: bytes
) -> tuple[Document, IngestedDocument]:
    """Store an uploaded file to disk, create a DB record, and ingest it.

    Args:
        filename: Original filename (e.g. "report.pdf").
        file_content: Raw bytes of the uploaded file.

    Returns:
        A tuple of (Document DB record, IngestedDocument).

    Raises:
        ValueError: If the file type is unsupported.
    """
    file_type = _file_type_from_filename(filename)

    # Generate a unique storage filename
    unique_prefix = uuid.uuid4().hex[:12]
    safe_name = f"{unique_prefix}_{filename}"
    originals_dir = get_settings().originals_dir
    dest_path = originals_dir / safe_name

    # Write file to disk
    dest_path.write_bytes(file_content)

    storage_path = str(dest_path.relative_to(originals_dir.parent.parent))

    # Ingest the document
    ingester = get_ingester(file_type)
    ingested = ingester.ingest(dest_path, storage_path)

    # Create DB record
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
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    return doc, ingested
