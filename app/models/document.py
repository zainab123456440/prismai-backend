from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

# --- Request Models ---

class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    status: str
    message: str

class DocumentStatusResponse(BaseModel):
    document_id: str
    filename: str
    status: str  # queued, processing, ready, failed
    chunk_count: Optional[int] = None
    created_at: datetime
    updated_at: datetime

# --- Document List ---

class DocumentItem(BaseModel):
    document_id: str
    filename: str
    file_type: str
    status: str
    chunk_count: Optional[int] = None
    summary: Optional[str] = None
    suggested_questions: Optional[List[str]] = None
    created_at: datetime

class DocumentListResponse(BaseModel):
    documents: List[DocumentItem]
    total: int

# --- Delete ---

class DocumentDeleteResponse(BaseModel):
    document_id: str
    message: str