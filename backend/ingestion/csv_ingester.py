"""CSV (.csv) document ingester using Python's built-in csv module."""

import csv
import io
from pathlib import Path

from backend.ingestion.common import (
    BaseIngester,
    IngestedDocument,
    register_ingester,
)


class CsvIngester(BaseIngester):
    """Extracts structured text from CSV files."""

    def ingest(self, file_path: Path, storage_path: str) -> IngestedDocument:
        """Ingest a CSV file.

        Reads the CSV and converts to a tab-separated text representation
        consistent with the Excel ingester output. page_count is always 1.

        Args:
            file_path: Path to the .csv file.
            storage_path: Relative storage path for reference.

        Returns:
            IngestedDocument with structured text and empty pages list.
        """
        raw_bytes = file_path.read_bytes()

        # Try UTF-8 first, fall back to latin-1 (which never raises)
        try:
            content = raw_bytes.decode("utf-8-sig")
        except UnicodeDecodeError:
            content = raw_bytes.decode("latin-1")

        reader = csv.reader(io.StringIO(content))
        lines: list[str] = []
        for row in reader:
            # Skip entirely empty rows
            if any(cell.strip() for cell in row):
                lines.append("\t".join(row))

        text = "\n".join(lines)

        return IngestedDocument(
            original_filename=file_path.name,
            storage_path=storage_path,
            file_type="csv",
            pages=[],
            text=text,
            page_count=1,
        )


register_ingester("csv", CsvIngester)
