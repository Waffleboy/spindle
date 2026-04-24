"""PDF document ingester using PyMuPDF (fitz)."""

from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image

from backend.config import get_settings
from backend.ingestion.common import (
    BaseIngester,
    IngestedDocument,
    register_ingester,
)


class PdfIngester(BaseIngester):
    """Extracts page images and text from PDF files."""

    def ingest(self, file_path: Path, storage_path: str) -> IngestedDocument:
        """Ingest a PDF file.

        Renders each page to a PIL Image at 150 DPI and extracts text.

        Args:
            file_path: Path to the PDF file.
            storage_path: Relative storage path for reference.

        Returns:
            IngestedDocument with page images and concatenated text.
        """
        render_dpi = get_settings().pdf_render_dpi
        zoom = render_dpi / 72

        doc = fitz.open(str(file_path))
        try:
            pages: list[Image.Image] = []
            text_parts: list[str] = []
            mat = fitz.Matrix(zoom, zoom)

            for page in doc:
                # Render page to image
                pix = page.get_pixmap(matrix=mat)
                img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                pages.append(img)

                # Extract text
                page_text = page.get_text()
                if page_text.strip():
                    text_parts.append(page_text)

            text = "\n\n".join(text_parts)

            return IngestedDocument(
                original_filename=file_path.name,
                storage_path=storage_path,
                file_type="pdf",
                pages=pages,
                text=text,
                metadata={"dpi": render_dpi},
                page_count=len(doc),
            )
        finally:
            doc.close()


register_ingester("pdf", PdfIngester)
