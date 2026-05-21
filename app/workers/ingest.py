from app.core.loader import load_to_markdown, get_file_type
from app.core.splitter import split_markdown
from app.core.embedder import embed_chunks
from app.db.qdrant import ensure_collection, store_chunks
from app.db.supabase import (
    update_document_status,
    save_document_summary,
    save_suggested_questions,
)
import os
import logging
import traceback

# --- Logger ---

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


# --- Main Ingestion Task ---

def ingest_document(
    file_path: str,
    file_type: str,
    document_id: str,
    user_id: str,
    filename: str,
):
    """
    Main background task that processes
    an uploaded document end to end.

    Flow:
    1. Update status to processing
    2. Load file and convert to markdown
    3. Split markdown into chunks
    4. Generate embeddings
    5. Store chunks in Qdrant
    6. Generate summary
    7. Generate suggested questions
    8. Update status to ready
    9. Clean up temp file

    If anything fails:
    - Status updated to failed
    - Temp file cleaned up regardless

    NOTE: Running as a plain function via ThreadPoolExecutor
    for local development (no Redis or Celery required).
    When deploying to production, wrap this back with
    @celery_app.task and use ingest_document.delay(...)
    in upload.py.
    """

    try:
        # ─────────────────────────────
        # Step 1 — Mark as processing
        # ─────────────────────────────
        logger.info(f"[{filename}] Step 1 — Marking as processing...")
        update_document_status(
            document_id=document_id,
            status="processing"
        )

        # ─────────────────────────────
        # Step 2 — Load + convert to markdown
        # ─────────────────────────────
        logger.info(f"[{filename}] Step 2 — Loading file and converting to markdown...")
        markdown_text = load_to_markdown(
            file_path=file_path,
            file_type=file_type,
        )

        if not markdown_text.strip():
            raise ValueError(
                f"Could not extract text from {filename}. "
                f"File may be empty or corrupted."
            )

        # ─────────────────────────────
        # Step 3 — Split into chunks
        # ─────────────────────────────
        logger.info(f"[{filename}] Step 3 — Splitting into chunks...")
        chunks = split_markdown(
            text=markdown_text,
            file_type=file_type,
        )

        if not chunks:
            raise ValueError(
                f"Could not split {filename} into chunks."
            )

        logger.info(f"[{filename}] Got {len(chunks)} chunks.")

        # ─────────────────────────────
        # Step 4 — Generate embeddings
        # ─────────────────────────────
        logger.info(f"[{filename}] Step 4 — Generating embeddings...")
        embeddings = embed_chunks(chunks)

        # ─────────────────────────────
        # Step 5 — Store in Qdrant
        # ─────────────────────────────
        logger.info(f"[{filename}] Step 5 — Storing chunks in Qdrant...")
        ensure_collection()

        store_chunks(
            chunks=chunks,
            embeddings=embeddings,
            document_id=document_id,
            user_id=user_id,
            filename=filename,
            file_type=file_type,
        )

        # ─────────────────────────────
        # Step 6 — Generate summary
        # ─────────────────────────────
       

        
        # ─────────────────────────────
        #

        
        # ─────────────────────────────
        # Step 8 — Mark as ready
        # ─────────────────────────────
        logger.info(f"[{filename}] Step 8 — Marking as ready!")
        update_document_status(
            document_id=document_id,
            status="ready",
            chunk_count=len(chunks),
        )

        # ─────────────────────────────
        # Step 9 — Clean up temp file
        # (only on success)
        # ─────────────────────────────
        logger.info(f"[{filename}] Step 9 — Cleaning up temp file.")
        cleanup_temp_file(file_path)

        logger.info(f"[{filename}] ✅ Done! Document is ready.")

    except Exception as exc:
        logger.error(f"[{filename}] ❌ FAILED at some step!")
        logger.error(traceback.format_exc())

        # Mark document as failed
        # and clean up temp file
        update_document_status(
            document_id=document_id,
            status="failed",
        )
        cleanup_temp_file(file_path)
        raise


# --- Cleanup ---

def cleanup_temp_file(file_path: str):
    """
    Deletes the temporary file after processing.
    Called only after success or final failure.
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception:
        pass  # Don't crash if cleanup fails