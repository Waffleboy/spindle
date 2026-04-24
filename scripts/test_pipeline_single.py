#!/usr/bin/env python3
"""Run the pipeline on a single file and print all LLM outputs.

Usage:
    uv run python scripts/test_pipeline_single.py path/to/file.pdf
    uv run python scripts/test_pipeline_single.py path/to/file.csv --skip-embeddings
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, patch

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.ingestion.common import get_ingester
from backend.pipeline.llm import llm_call as _original_llm_call, parse_json_response


_STEP_LABEL = ""


def _format_json(data):
    return json.dumps(data, indent=2, default=str)


async def _traced_llm_call(**kwargs):
    """Wrapper that prints prompt/response for every LLM call."""
    prompt = kwargs.get("prompt", "")
    system = kwargs.get("system", "")
    images = kwargs.get("images")

    print(f"\n{'='*80}")
    print(f"  LLM CALL — {_STEP_LABEL}")
    print(f"{'='*80}")
    print(f"\n--- System ---\n{system}")
    print(f"\n--- Prompt ({len(prompt)} chars) ---")
    # Truncate very long prompts for readability
    if len(prompt) > 3000:
        print(prompt[:1500])
        print(f"\n  ... [{len(prompt) - 3000} chars truncated] ...\n")
        print(prompt[-1500:])
    else:
        print(prompt)
    if images:
        print(f"\n  [+ {len(images)} image(s) attached]")

    t0 = time.perf_counter()
    response = await _original_llm_call(**kwargs)
    elapsed = time.perf_counter() - t0

    print(f"\n--- Response ({elapsed:.1f}s) ---")
    # Pretty-print if JSON
    try:
        parsed = parse_json_response(response)
        print(_format_json(parsed))
    except Exception:
        print(response)

    return response


async def main():
    parser = argparse.ArgumentParser(description="Run pipeline on a single file")
    parser.add_argument("file", help="Path to the document file")
    parser.add_argument("--skip-embeddings", action="store_true",
                        help="Skip the embedding/chunking step")
    args = parser.parse_args()

    filepath = Path(args.file).resolve()
    if not filepath.exists():
        print(f"Error: {filepath} does not exist", file=sys.stderr)
        sys.exit(1)

    ext = filepath.suffix.lower().lstrip(".")
    ext_map = {"pdf": "pdf", "docx": "docx", "doc": "doc",
               "xlsx": "xlsx", "xls": "xls", "csv": "csv"}
    file_type = ext_map.get(ext)
    if not file_type:
        print(f"Error: unsupported file type .{ext}", file=sys.stderr)
        sys.exit(1)

    # Ingest
    print(f"\n  Ingesting {filepath.name} ...")
    ingester = get_ingester(file_type)
    ingested = ingester.ingest(filepath, str(filepath))
    print(f"  File type: {file_type}")
    print(f"  Text length: {len(ingested.text or '')} chars")
    print(f"  Pages: {ingested.page_count}")

    global _STEP_LABEL

    # --- Step 1: Doc type detection ---
    _STEP_LABEL = "Step 1 — Doc Type Detection"
    print(f"\n{'#'*80}")
    print(f"  STEP 1: Document Type Detection & Date Extraction")
    print(f"{'#'*80}")

    from backend.pipeline.step1_doc_type import detect_doc_type

    # Use an in-memory DB
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from backend.database import Base
    import backend.models  # noqa: F401
    from backend.models import Document, TaxonomySchema

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    # Create a Document record
    doc_record = Document(
        original_filename=filepath.name,
        storage_path=str(filepath),
        file_type=file_type,
        page_count=ingested.page_count,
    )
    db.add(doc_record)
    db.commit()
    db.refresh(doc_record)

    with patch("backend.pipeline.step1_doc_type.llm_call", side_effect=_traced_llm_call):
        doc_type = await detect_doc_type(
            documents=[ingested],
            document_ids=[doc_record.id],
            db=db,
        )

    db.refresh(doc_record)
    print(f"\n  >> Doc type: {doc_type}")
    print(f"  >> Report date: {doc_record.report_date}")

    # --- Step 2: Taxonomy generation ---
    _STEP_LABEL = "Step 2 — Taxonomy Generation"
    print(f"\n{'#'*80}")
    print(f"  STEP 2: Taxonomy Generation")
    print(f"{'#'*80}")

    from backend.pipeline.step2_taxonomy import generate_taxonomy

    with patch("backend.pipeline.step2_taxonomy.llm_call", side_effect=_traced_llm_call):
        taxonomy = await generate_taxonomy(
            doc_type=doc_type,
            documents=[ingested],
            db=db,
        )

    print(f"\n  >> Taxonomy ({len(taxonomy.dimensions)} dimensions):")
    for dim in taxonomy.dimensions:
        print(f"     - {dim['name']} ({dim['expected_type']}): {dim['description']}")

    # --- Step 3: Extraction ---
    _STEP_LABEL = "Step 3 — Per-Document Extraction"
    print(f"\n{'#'*80}")
    print(f"  STEP 3: Per-Document Extraction")
    print(f"{'#'*80}")

    from backend.pipeline.step3_extraction import fetch_extraction_data, save_extraction_results

    if args.skip_embeddings:
        async def _no_embed(document):
            return None
        embed_patch = patch("backend.pipeline.step3_extraction._fetch_embeddings", side_effect=_no_embed)
    else:
        from contextlib import nullcontext
        embed_patch = nullcontext()

    with patch("backend.pipeline.step3_extraction.llm_call", side_effect=_traced_llm_call), embed_patch:
        extracted_data, chunks = await fetch_extraction_data(ingested, taxonomy)

    extractions = save_extraction_results(doc_record.id, taxonomy, extracted_data, chunks, db)

    print(f"\n  >> Extractions ({len(extractions)}):")
    for ext in extractions:
        print(f"     - {ext.dimension_name}: {ext.raw_value!r}  (confidence={ext.confidence:.2f})")

    if chunks:
        print(f"  >> Chunks: {len(chunks)} embedded")
    else:
        print(f"  >> Chunks: skipped")

    # --- Step 4: Entity Resolution ---
    _STEP_LABEL = "Step 4 — Entity Resolution"
    print(f"\n{'#'*80}")
    print(f"  STEP 4: Entity Resolution")
    print(f"{'#'*80}")

    from backend.pipeline.step4_entities import resolve_entities

    with patch("backend.pipeline.step4_entities.llm_call", side_effect=_traced_llm_call):
        entities = await resolve_entities(taxonomy=taxonomy, db=db)

    if entities:
        print(f"\n  >> Entities ({len(entities)}):")
        for ent in entities:
            print(f"     - {ent.canonical_name} ({ent.entity_type}) aliases={ent.aliases}")
    else:
        print(f"\n  >> No entities to resolve (no entity-type dimensions)")

    # --- Step 5: Contradiction Detection ---
    _STEP_LABEL = "Step 5 — Contradiction Detection"
    print(f"\n{'#'*80}")
    print(f"  STEP 5: Contradiction Detection")
    print(f"{'#'*80}")

    print(f"\n  >> Skipped (need 2+ documents for contradiction detection)")

    # --- Summary ---
    print(f"\n{'#'*80}")
    print(f"  SUMMARY")
    print(f"{'#'*80}")
    print(f"  File: {filepath.name}")
    print(f"  Doc type: {doc_type}")
    print(f"  Report date: {doc_record.report_date}")
    print(f"  Dimensions: {len(taxonomy.dimensions)}")
    print(f"  Extractions: {len(extractions)}")
    print(f"  Entities: {len(entities)}")

    db.close()


if __name__ == "__main__":
    asyncio.run(main())
