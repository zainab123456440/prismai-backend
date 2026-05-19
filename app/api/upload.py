from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Depends,
    HTTPException,
    status,
)
from app.models.document import (
    DocumentUploadResponse,
    DocumentStatusResponse,
)
from app.auth.dependencies import get_current_user
from app.models.user import CurrentUser
from app.db.supabase import (
    create_document_record,
    get_document_status,
)
from app.core.loader import get_file_type
from app.workers.ingest import ingest_document
from app.config import settings
import asyncio
from concurrent.futures import ThreadPoolExecutor
import shutil
import uuid
import os

# --- Router ---

router = APIRouter(
    prefix="/upload",
    tags=["Upload"]
)

# --- Thread Pool for background tasks ---

executor = ThreadPoolExecutor()

# --- Allowed File Types ---

ALLOWED_CONTENT_TYPES = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument"
    ".wordprocessingml.document": "docx",
    "text/csv": "csv",
    "application/vnd.openxmlformats-officedocument"
    ".spreadsheetml.sheet": "xlsx",
    "text/plain": "txt",
}


# --- Upload Endpoint ---

@router.post(
    "/",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_document(
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Accepts a file upload and queues it
    for background processing.
    Returns immediately with document_id
    and status queued.
    User does not wait for processing.
    """

    # ─────────────────────────────
    # Step 1 — Validate file type
    # ─────────────────────────────
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported file type: {file.content_type}. "
                f"Allowed: PDF, DOCX, CSV, Excel, TXT"
            )
        )

    file_type = ALLOWED_CONTENT_TYPES[file.content_type]

    # ─────────────────────────────
    # Step 2 — Validate file size
    # ─────────────────────────────
    max_bytes = settings.max_file_size_mb * 1024 * 1024

    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to start

    if file_size > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"File too large. "
                f"Maximum size is {settings.max_file_size_mb}MB"
            )
        )

    # ─────────────────────────────
    # Step 3 — Generate document ID
    # ─────────────────────────────
    document_id = str(uuid.uuid4())

    # ─────────────────────────────
    # Step 4 — Save file temporarily
    # ─────────────────────────────
    os.makedirs("uploads", exist_ok=True)

    temp_path = f"uploads/{document_id}_{file.filename}"

    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # ─────────────────────────────
    # Step 5 — Create DB record
    # ─────────────────────────────
    create_document_record(
        document_id=document_id,
        user_id=current_user.id,
        filename=file.filename,
        file_type=file_type,
        status="queued",
    )

    # ─────────────────────────────
    # Step 6 — Run in background thread
    # (no Redis or Celery needed locally)
    # When deploying: swap this block back
    # to ingest_document.delay(...)
    # ─────────────────────────────
    loop = asyncio.get_event_loop()
    loop.run_in_executor(
        executor,
        lambda: ingest_document(
            file_path=temp_path,
            file_type=file_type,
            document_id=document_id,
            user_id=current_user.id,
            filename=file.filename,
        )
    )

    # ─────────────────────────────
    # Step 7 — Return immediately
    # ─────────────────────────────
    return DocumentUploadResponse(
        document_id=document_id,
        filename=file.filename,
        status="queued",
        message=(
            "Document uploaded successfully. "
            "Processing in background. "
            "Poll /upload/status/{document_id} for updates."
        )
    )


# --- Status Endpoint ---

@router.get(
    "/status/{document_id}",
    response_model=DocumentStatusResponse,
)
async def get_upload_status(
    document_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Returns current processing status
    of an uploaded document.
    Frontend polls this every 3 seconds
    until status is ready or failed.

    Status flow:
    queued → processing → ready
                       → failed
    """

    document = get_document_status(document_id)

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Security check — users can only
    # check their own documents
    if document["user_id"] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    return DocumentStatusResponse(
        document_id=document["id"],
        filename=document["filename"],
        status=document["status"],
        chunk_count=document.get("chunk_count"),
        created_at=document["created_at"],
        updated_at=document["updated_at"],
    )