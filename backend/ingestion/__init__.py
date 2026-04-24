"""Document ingestion layer — converts PDF, Word, and Excel files into a common representation."""

from backend.ingestion.common import IngestedDocument, get_ingester

__all__ = ["IngestedDocument", "get_ingester"]
