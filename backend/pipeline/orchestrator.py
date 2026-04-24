"""Pipeline orchestrator — runs the full 5-step pipeline on a set of documents."""

import asyncio
import logging
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

from sqlalchemy.orm import Session

from backend.ingestion.common import IngestedDocument, get_ingester
from backend.models import Document
from backend.pipeline.step1_doc_type import detect_doc_type
from backend.pipeline.step2_taxonomy import generate_taxonomy
from backend.pipeline.step3_extraction import fetch_extraction_data, save_extraction_results
from backend.pipeline.step4_entities import resolve_entities
from backend.pipeline.step5_contradictions import detect_contradictions
from backend.pipeline.template_matching import match_templates

# Module-level status dict for polling by the API layer
pipeline_status: dict = {}


def _update_status(
    run_id: str,
    step: int,
    description: str,
    percentage: int,
    status: str = "running",
    error: str = None,
):
    """Update the module-level pipeline status dict."""
    pipeline_status[run_id] = {
        "run_id": run_id,
        "step": step,
        "total_steps": 5,
        "description": description,
        "percentage": percentage,
        "status": status,
        "error": error,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


async def run_pipeline(
    document_ids: list[str],
    company_context: str = None,
    db: Session = None,
) -> dict:
    """Run the full 5-step pipeline on a set of documents.

    Steps:
        1. Document type detection
        2. Taxonomy generation
        3. Per-document extraction (with chunking and embedding)
        4. Entity resolution
        5. Contradiction detection

    Args:
        document_ids: List of Document DB record IDs to process.
        company_context: Optional company/domain context string.
        db: SQLAlchemy session.

    Returns:
        Status dict with pipeline results and progress info.
    """
    run_id = str(uuid.uuid4())
    corpus_id = str(uuid.uuid4())

    try:
        # Load document records
        documents_db = []
        for doc_id in document_ids:
            doc = db.query(Document).filter(Document.id == doc_id).first()
            if doc:
                documents_db.append(doc)

        if not documents_db:
            _update_status(run_id, 0, "No documents found", 0, status="error",
                           error="No valid document IDs provided")
            return pipeline_status[run_id]

        # Re-ingest documents to get IngestedDocument objects
        ingested_docs = []
        for doc_record in documents_db:
            if doc_record.source_text:
                ingested = IngestedDocument(
                    original_filename=doc_record.original_filename,
                    storage_path=doc_record.storage_path,
                    file_type=doc_record.file_type,
                    pages=[],
                    text=doc_record.source_text,
                    page_count=doc_record.page_count or 1,
                )
            else:
                ingester = get_ingester(doc_record.file_type)
                file_path = Path(doc_record.storage_path)
                if not file_path.is_absolute():
                    file_path = Path.cwd() / file_path
                ingested = ingester.ingest(file_path, doc_record.storage_path)
            ingested_docs.append(ingested)

        # Step 1: Document Type Detection
        _update_status(run_id, 1, "Detecting document types...", 10)
        doc_type = await detect_doc_type(
            documents=ingested_docs,
            document_ids=document_ids,
            db=db,
        )

        # Template matching: LLM decides which templates apply
        sample_text = " ".join(
            (doc.text or "")[:800] for doc in ingested_docs[:2]
        )
        matched = await match_templates(
            doc_type=doc_type,
            sample_text=sample_text,
            db=db,
        )

        # Step 2: Taxonomy Generation
        _update_status(run_id, 2, "Generating taxonomy schema...", 25)
        taxonomy = await generate_taxonomy(
            doc_type=doc_type,
            documents=ingested_docs,
            corpus_id=corpus_id,
            company_context=company_context,
            matched_templates=matched,
            db=db,
        )

        # Step 3: Per-Document Extraction
        # Phase A: parallel LLM + embedding calls (no DB writes)
        _update_status(run_id, 3, f"Extracting data from {len(ingested_docs)} documents...", 40)

        io_results = await asyncio.gather(
            *(fetch_extraction_data(ing, taxonomy) for ing in ingested_docs)
        )

        # Phase B: sequential DB writes
        _update_status(run_id, 3, "Saving extraction results...", 65)
        all_extractions = []
        for doc_id, (extracted_data, chunks_with_embeddings) in zip(document_ids, io_results):
            extractions = save_extraction_results(
                doc_id, taxonomy, extracted_data, chunks_with_embeddings, db,
            )
            all_extractions.extend(extractions)

        _update_status(run_id, 3, "Extraction complete", 70)
        now = datetime.now(timezone.utc)
        for doc_id in document_ids:
            doc_record = db.query(Document).filter(Document.id == doc_id).first()
            if doc_record:
                doc_record.processed_at = now
        db.commit()

        # Step 4: Entity Resolution
        _update_status(run_id, 4, "Resolving entities...", 75)
        entities = await resolve_entities(taxonomy=taxonomy, db=db)

        # Step 5: Contradiction Detection
        _update_status(run_id, 5, "Detecting contradictions...", 90)
        contradictions = await detect_contradictions(taxonomy=taxonomy, db=db)

        # Done
        _update_status(run_id, 5, "Pipeline complete", 100, status="complete")
        pipeline_status[run_id].update({
            "doc_type": doc_type,
            "taxonomy_id": taxonomy.id,
            "num_extractions": len(all_extractions),
            "num_entities": len(entities),
            "num_contradictions": len(contradictions),
        })

        return pipeline_status[run_id]

    except Exception as e:
        step = pipeline_status.get(run_id, {}).get("step", 0)
        error_detail = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        logger.error("Pipeline failed at step %d: %s", step, error_detail)
        _update_status(
            run_id, step,
            f"Pipeline failed at step {step}",
            pipeline_status.get(run_id, {}).get("percentage", 0),
            status="error",
            error=error_detail,
        )
        return pipeline_status[run_id]
