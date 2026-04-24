"""CSV (.csv) document ingester using Python's built-in csv module."""

import csv
import io
from pathlib import Path

from backend.ingestion.common import (
    BaseIngester,
    IngestedDocument,
    register_ingester,
)


def _read_csv_content(file_path: Path) -> str:
    raw_bytes = file_path.read_bytes()
    try:
        return raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw_bytes.decode("latin-1")


class CsvIngester(BaseIngester):
    """Extracts structured text from CSV files."""

    def ingest(self, file_path: Path, storage_path: str) -> IngestedDocument:
        content = _read_csv_content(file_path)
        reader = csv.reader(io.StringIO(content))
        lines: list[str] = []
        for row in reader:
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

    def ingest_rows(
        self, file_path: Path, storage_path: str, original_filename: str | None = None
    ) -> list[IngestedDocument]:
        """Split a CSV into one IngestedDocument per data row.

        Each document's text is a key-value representation using the header
        row as field names, making it easier for the LLM to extract from.
        """
        content = _read_csv_content(file_path)
        reader = csv.reader(io.StringIO(content))

        rows = [r for r in reader if any(cell.strip() for cell in r)]
        if len(rows) < 2:
            return [self.ingest(file_path, storage_path)]

        base_name = original_filename or file_path.name
        headers = rows[0]
        documents: list[IngestedDocument] = []

        for row_idx, row in enumerate(rows[1:], start=1):
            kv_lines: list[str] = []
            for col_idx, cell in enumerate(row):
                header = headers[col_idx] if col_idx < len(headers) else f"Column {col_idx + 1}"
                kv_lines.append(f"{header}: {cell}")
            text = "\n".join(kv_lines)

            documents.append(IngestedDocument(
                original_filename=f"{base_name} [Row {row_idx}]",
                storage_path=storage_path,
                file_type="csv",
                pages=[],
                text=text,
                page_count=1,
            ))

        return documents


register_ingester("csv", CsvIngester)
