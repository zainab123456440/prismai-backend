from pydantic import BaseModel
from datetime import datetime
from typing import List

# --- Queries Per Day ---

class QueriesPerDayItem(BaseModel):
    date: str
    query_count: int

class QueriesPerDayResponse(BaseModel):
    data: List[QueriesPerDayItem]
    total_queries: int

# --- Top Documents ---

class TopDocumentItem(BaseModel):
    document_id: str
    filename: str
    query_count: int

class TopDocumentsResponse(BaseModel):
    data: List[TopDocumentItem]

# --- Response Times ---

class ResponseTimeItem(BaseModel):
    date: str
    avg_response_time_ms: int

class ResponseTimesResponse(BaseModel):
    data: List[ResponseTimeItem]
    overall_avg_ms: int

# --- Popular Questions ---

class PopularQuestionItem(BaseModel):
    question: str
    asked_count: int

class PopularQuestionsResponse(BaseModel):
    data: List[PopularQuestionItem]

# --- Dashboard Summary ---

class DashboardSummaryResponse(BaseModel):
    total_documents: int
    total_queries: int
    total_users: int
    avg_response_time_ms: int
    queries_today: int
    documents_ready: int
    documents_processing: int