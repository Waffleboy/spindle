"""Common interface and data structures for document ingestion."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image


@dataclass
class IngestedDocument:
    """Intermediate representation of an ingested document.

    Used to pass structured data from format-specific ingesters
    into the downstream LLM processing pipeline.
    """

    original_filename: str
    storage_path: str
    file_type: str  # "pdf", "docx", "doc", "xlsx", "xls", "csv"
    pages: list  # list of PIL.Image for PDFs, empty for text formats
    text: str  # extracted text content
    metadata: dict = field(default_factory=dict)
    page_count: int = 0


class BaseIngester(ABC):
    """Abstract base class for all document format ingesters."""

    @abstractmethod
    def ingest(self, file_path: Path, storage_path: str) -> IngestedDocument:
        """Ingest a document file and return an IngestedDocument.

        Args:
            file_path: Path to the file on disk.
            storage_path: Relative storage path for reference.

        Returns:
            IngestedDocument with extracted content.
        """
        ...


# Registry of file_type -> ingester class (populated lazily)
_INGESTER_REGISTRY: dict[str, type[BaseIngester]] = {}


def register_ingester(file_type: str, ingester_cls: type[BaseIngester]) -> None:
    """Register an ingester class for a given file type."""
    _INGESTER_REGISTRY[file_type] = ingester_cls


def get_ingester(file_type: str) -> BaseIngester:
    """Return an instantiated ingester for the given file type.

    Args:
        file_type: One of "pdf", "docx", "doc", "xlsx", "xls", "csv".

    Returns:
        An instance of the appropriate BaseIngester subclass.

    Raises:
        ValueError: If the file type is not supported.
    """
    # Trigger registration of all ingesters on first call
    if not _INGESTER_REGISTRY:
        _load_ingesters()

    cls = _INGESTER_REGISTRY.get(file_type)
    if cls is None:
        supported = ", ".join(sorted(_INGESTER_REGISTRY.keys()))
        raise ValueError(
            f"Unsupported file type: {file_type!r}. Supported types: {supported}"
        )
    return cls()


def _load_ingesters() -> None:
    """Import ingester modules to trigger their registration."""
    import backend.ingestion.pdf_ingester  # noqa: F401
    import backend.ingestion.word_ingester  # noqa: F401
    import backend.ingestion.excel_ingester  # noqa: F401
    import backend.ingestion.csv_ingester  # noqa: F401
