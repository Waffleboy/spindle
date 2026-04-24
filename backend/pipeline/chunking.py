"""Text chunking utility for splitting documents into overlapping chunks."""


from backend.config import get_settings


def chunk_text(
    text: str,
    chunk_size: int | None = None,
    overlap: int | None = None,
) -> list[dict]:
    """Split text into overlapping chunks by word count.

    Args:
        text: The full text to chunk.
        chunk_size: Target number of words per chunk (default from settings).
        overlap: Number of overlapping words between consecutive chunks (default from settings).

    Returns:
        List of dicts with keys: text, chunk_index, approx_pages.
    """
    cfg = get_settings()
    chunk_size = chunk_size if chunk_size is not None else cfg.chunk_size
    overlap = overlap if overlap is not None else cfg.chunk_overlap

    if not text or not text.strip():
        return []

    words = text.split()
    if not words:
        return []

    chunks = []
    chunk_index = 0
    start = 0
    step = max(chunk_size - overlap, 1)
    words_per_page = cfg.words_per_page

    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk_words = words[start:end]
        chunk_text_str = " ".join(chunk_words)

        # Estimate which pages this chunk covers
        start_page = start // words_per_page + 1
        end_page = (end - 1) // words_per_page + 1
        approx_pages = list(range(start_page, end_page + 1))

        chunks.append(
            {
                "text": chunk_text_str,
                "chunk_index": chunk_index,
                "approx_pages": approx_pages,
            }
        )

        chunk_index += 1
        start += step

        # If we already reached the end, stop
        if end >= len(words):
            break

    return chunks
