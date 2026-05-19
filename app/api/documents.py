from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime
import logging

from app.models.document import (
    DocumentListResponse,
    DocumentItem,
    DocumentDeleteResponse,
)
from app.auth.dependencies import get_current_user
from app.models.user import CurrentUser
from app.db.supabase import (
    get_user_documents,
    get_document_status,
    delete_document_record,
)
from app.db.qdrant import delete_document_chunks

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/documents",
    tags=["Documents"]
)


# List Documents
@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    current_user: CurrentUser = Depends(get_current_user),
):
    """Return all documents of the current user."""

    documents = get_user_documents(user_id=current_user.id)

    document_items = [
        DocumentItem(
            document_id=doc["id"],
            filename=doc["filename"],
            file_type=doc["file_type"],
            status=doc["status"],
            chunk_count=doc.get("chunk_count"),
            summary=doc.get("summary"),
            suggested_questions=doc.get("suggested_questions", []),
            created_at=doc["created_at"],
        )
        for doc in documents
    ]

    return DocumentListResponse(
        documents=document_items,
        total=len(document_items),
    )


# Get Single Document
@router.get("/{document_id}", response_model=DocumentItem)
async def get_document(
    document_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    document = get_document_status(document_id)

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if document["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return DocumentItem(
        document_id=document["id"],
        filename=document["filename"],
        file_type=document["file_type"],
        status=document["status"],
        chunk_count=document.get("chunk_count"),
        summary=document.get("summary"),
        suggested_questions=document.get("suggested_questions", []),
        created_at=document["created_at"],
    )


# Delete Document
@router.delete("/{document_id}", response_model=DocumentDeleteResponse)
async def delete_document(
    document_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    logger.info(f"🗑️ Delete requested — document_id: {document_id}, user_id: {current_user.id}")

    # --- Step 1: Fetch document ---
    document = get_document_status(document_id)

    if not document:
        logger.warning(f"Document not found: {document_id}")
        raise HTTPException(status_code=404, detail="Document not found")

    if document["user_id"] != current_user.id:
        logger.warning(f"Access denied — document belongs to {document['user_id']}, request from {current_user.id}")
        raise HTTPException(status_code=403, detail="Access denied")

    # --- Step 2: Delete vectors from Qdrant ---
    try:
        logger.info(f"Deleting Qdrant chunks for document_id: {document_id}")
        delete_document_chunks(document_id=document_id, user_id=current_user.id)
        logger.info(f"✅ Qdrant chunks deleted for document_id: {document_id}")
    except Exception as e:
        # Non-fatal: log and continue so metadata is still cleaned up
        logger.error(f"❌ Qdrant deletion failed for document_id {document_id}: {e}")

    # --- Step 3: Delete metadata from Supabase ---
    try:
        logger.info(f"Deleting Supabase record for document_id: {document_id}")
        delete_document_record(document_id=document_id, user_id=current_user.id)
        logger.info(f"✅ Supabase record deleted for document_id: {document_id}")
    except Exception as e:
        logger.error(f"❌ Supabase deletion failed for document_id {document_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete document record: {str(e)}"
        )

    logger.info(f"✅ Document '{document['filename']}' fully deleted.")

    return DocumentDeleteResponse(
        document_id=document_id,
        message=f"{document['filename']} deleted successfully"
    )


# Suggested Questions
@router.get("/{document_id}/questions")
async def get_document_questions(
    document_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    document = get_document_status(document_id)
    if not document or document["user_id"] != current_user.id:
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "document_id": document_id,
        "filename": document["filename"],
        "suggested_questions": document.get("suggested_questions", []),
    }


# Summary
@router.get("/{document_id}/summary")
async def get_document_summary(
    document_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    document = get_document_status(document_id)
    if not document or document["user_id"] != current_user.id:
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "document_id": document_id,
        "filename": document["filename"],
        "summary": document.get("summary"),
    }