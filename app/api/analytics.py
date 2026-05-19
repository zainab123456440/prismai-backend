from fastapi import APIRouter, Depends
from app.auth.dependencies import get_current_user
from app.models.user import CurrentUser
from app.models.analytics import (
    QueriesPerDayResponse,
    QueriesPerDayItem,
    ResponseTimesResponse,
    ResponseTimeItem,
)
from app.db.supabase import (
    get_queries_per_day,
    get_query_history,
)

# --- Router ---

router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"]
)

# --- Queries Per Day ---

@router.get(
    "/queries-per-day",
    response_model=QueriesPerDayResponse,
)
async def get_queries_per_day_chart(
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Returns query counts per day for the last 30 days.
    Frontend plots this as a line chart to show usage trends over time.
    """
    data = get_queries_per_day(current_user.id)

    items = [
        QueriesPerDayItem(
            date=item["date"],
            query_count=item["query_count"],
        )
        for item in data
    ]

    total = sum(item.query_count for item in items)

    return QueriesPerDayResponse(
        data=items,
        total_queries=total,
    )


# --- Response Times ---

@router.get(
    "/response-times",
    response_model=ResponseTimesResponse,
)
async def get_response_times_chart(
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Returns average response times grouped by day.
    """
    queries = get_query_history(
        user_id=current_user.id,
        limit=1000,
    )

    # Group by date
    by_date = {}

    for query in queries:
        # Parse date from created_at
        created_at = query["created_at"]
        if isinstance(created_at, str):
            date = created_at.split("T")[0]
        else:
            date = created_at.date().isoformat()

        if date not in by_date:
            by_date[date] = []

        by_date[date].append(query["response_time_ms"])

    # Calculate averages
    items = [
        ResponseTimeItem(
            date=date,
            avg_response_time_ms=int(
                sum(times) / len(times)
            ),
        )
        for date, times in sorted(by_date.items())
    ]

    overall_avg = (
        int(sum(
            item.avg_response_time_ms
            for item in items
        ) / len(items))
        if items else 0
    )

    return ResponseTimesResponse(
        data=items,
        overall_avg_ms=overall_avg,
    )


# --- Query History ---

@router.get(
    "/query-history",
)
async def get_query_history_chart(
    limit: int = 50,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Returns full query history.
    All past questions and answers for the logged in user.
    """
    from app.models.query import (
        QueryHistoryResponse,
        QueryHistoryItem,
    )

    queries = get_query_history(
        user_id=current_user.id,
        limit=limit,
    )

    items = [
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
        queries=items,
        total=len(items),
    )


# --- User Stats ---

@router.get(
    "/user-stats",
)
async def get_user_stats(
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Returns detailed user statistics and personal usage metrics.
    """
    from app.db.supabase import get_user_documents

    queries = get_query_history(
        user_id=current_user.id,
        limit=500,
    )

    documents = get_user_documents(
        current_user.id
    )

    # Calculate stats
    total_queries = len(queries)
    avg_response_time = (
        int(
            sum(q["response_time_ms"] for q in queries) / len(queries)
        ) if queries else 0
    )

    # Most active day
    by_date = {}
    for query in queries:
        created_at = query["created_at"]
        if isinstance(created_at, str):
            date = created_at.split("T")[0]
        else:
            date = created_at.date().isoformat()

        by_date[date] = by_date.get(date, 0) + 1

    most_active_day = (
        max(by_date.items(), key=lambda x: x[1])[0]
        if by_date else None
    )

    # Document stats
    total_documents = len(documents)
    docs_ready = len([
        d for d in documents
        if d["status"] == "ready"
    ])
    docs_processing = len([
        d for d in documents
        if d["status"] == "processing"
    ])

    return {
        "user_id": current_user.id,
        "email": current_user.email,
        "total_queries": total_queries,
        "avg_response_time_ms": avg_response_time,
        "most_active_day": most_active_day,
        "total_documents": total_documents,
        "documents_ready": docs_ready,
        "documents_processing": docs_processing,
    }