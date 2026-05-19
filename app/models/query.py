from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

# --- Request Models ---

class QueryRequest(BaseModel):
    question: str
    document_id: Optional[str] = None
    top_k: Optional[int] = 5

# --- Citation Model ---

class Citation(BaseModel):
    filename: str
    chunk_text: str
    relevance_score: float
    chunk_index: int

# --- Response Models ---

class QueryResponse(BaseModel):
    question: str
    answer: str
    citations: List[Citation]
    document_id: Optional[str] = None
    response_time_ms: int

# --- Query History ---

class QueryHistoryItem(BaseModel):
    query_id: str
    question: str
    answer: str
    document_id: Optional[str] = None
    response_time_ms: int
    created_at: datetime

class QueryHistoryResponse(BaseModel):
    queries: List[QueryHistoryItem]
    total: int