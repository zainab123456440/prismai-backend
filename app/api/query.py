from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from app.models.query import (
    QueryRequest,
    QueryResponse,
    QueryHistoryResponse,
    QueryHistoryItem,
    Citation,
)
from app.auth.dependencies import get_current_user
from app.models.user import CurrentUser
from app.core.generator import generate_answer
from app.db.supabase import (
    log_query,
    get_query_history,
    get_document_status,
)
from datetime import datetime

# --- Router ---

router = APIRouter(
    prefix="/query",
    tags=["Query"]
)


# --- Main Query Endpoint ---

@router.post(
    "/",
    response_model=QueryResponse,
)
async def query_documents(
    request: QueryRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    # ─────────────────────────────
    # Step 1 — Validate question
    # ─────────────────────────────
    question = request.question.strip()

    if not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty"
        )


    if len(question) > 1500:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question too long. Max 1000 characters"
        )

    # ─────────────────────────────
    # Step 2 — Validate document
    # ownership if document_id given
    # ─────────────────────────────
    if request.document_id:
        document = get_document_status(
            request.document_id
        )

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )

        if document["user_id"] != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

        if document["status"] != "ready":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Document is not ready yet. "
                    f"Current status: {document['status']}"
                )
            )

    # ─────────────────────────────
    # Step 3 — Run RAG pipeline
    # ─────────────────────────────
    try:
        result = generate_answer(
            question=question,
            user_id=current_user.id,
            document_id=request.document_id,
            top_k=request.top_k,
        )

    except Exception as e:
        print(f"❌ RAG pipeline error: {e}")          # ← shows real error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error: {str(e)}"                 # ← returns real error
        )

    # ─────────────────────────────
    # Step 4 — Log to analytics
    # ─────────────────────────────
    try:
        log_query(
            user_id=current_user.id,
            question=question,
            answer=result["answer"],
            document_id=request.document_id,
            response_time_ms=result["response_time_ms"],
        )
    except Exception:
        pass

    # ─────────────────────────────
    # Step 5 — Return response
    # ─────────────────────────────
    citations = [
        Citation(
            filename=c["filename"],
            chunk_text=c["chunk_text"],
            relevance_score=c["relevance_score"],
            chunk_index=c["chunk_index"],
        )
        for c in result["citations"]
    ]

    return QueryResponse(
        question=question,
        answer=result["answer"],
        citations=citations,
        document_id=request.document_id,
        response_time_ms=result["response_time_ms"],
    )


# --- Query History Endpoint ---

@router.get(
    "/history",
    response_model=QueryHistoryResponse,
)
async def get_history(
    limit: int = 50,
    current_user: CurrentUser = Depends(get_current_user),
):
    queries = get_query_history(
        user_id=current_user.id,
        limit=limit,
    )

    history_items = [
        QueryHistoryItem(
            query_id=q["id"],
            question=q["question"],
            answer=q["answer"],
            document_id=q.get("document_id"),
            response_time_ms=q["response_time_ms"],
            created_at=q["created_at"],
        )
        for q in queries
    ]

    return QueryHistoryResponse(
        queries=history_items,
        total=len(history_items),
    )