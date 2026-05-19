from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue
)
from app.config import settings
import uuid

# --- Client Connection ---

client = QdrantClient(
    url=settings.qdrant_url,
    api_key=settings.qdrant_api_key,
)

VECTOR_SIZE = 1536  # text-embedding-3-small dimension size

# --- Collection Setup ---
def ensure_collection():
    collections = client.get_collections().collections
    names = [c.name for c in collections]

    if settings.qdrant_collection in names:
        client.delete_collection(settings.qdrant_collection)
        print(f"Deleted old Qdrant collection: {settings.qdrant_collection}")

    client.create_collection(
        collection_name=settings.qdrant_collection,
        vectors_config=VectorParams(
            size=VECTOR_SIZE,
            distance=Distance.COSINE
        )
    )

    # ← Add these — required for filtering to work
    client.create_payload_index(
        collection_name=settings.qdrant_collection,
        field_name="user_id",
        field_schema="keyword",
    )
    client.create_payload_index(
        collection_name=settings.qdrant_collection,
        field_name="document_id",
        field_schema="keyword",
    )

    print(f"Created Qdrant collection: {settings.qdrant_collection}")
       


# --- Store Chunks ---

def store_chunks(
    chunks: list[str],
    embeddings: list[list[float]],
    document_id: str,
    user_id: str,
    filename: str,
    file_type: str,
):
    """
    Stores document chunks with embeddings in Qdrant.
    Every chunk is tagged with user_id for data isolation.
    """
    points = []

    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        points.append(
            PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload={
                    "text": chunk,
                    "document_id": document_id,
                    "user_id": user_id,
                    "filename": filename,
                    "file_type": file_type,
                    "chunk_index": i,
                }
            )
        )

    client.upsert(
        collection_name=settings.qdrant_collection,
        points=points
    )


# --- Search Chunks ---

def search_chunks(
    query_embedding: list[float],
    user_id: str,
    document_id: str = None,
    top_k: int = 5,
) -> list[dict]:
    """
    Searches for relevant chunks.
    ALWAYS filters by user_id — no data leaks between users.
    Optionally filters by document_id.
    """
    must_conditions = [
        FieldCondition(
            key="user_id",
            match=MatchValue(value=user_id)
        )
    ]

    if document_id:
        must_conditions.append(
            FieldCondition(
                key="document_id",
                match=MatchValue(value=document_id)
            )
        )

    results = client.query_points(
        collection_name=settings.qdrant_collection,
        query=query_embedding,
        query_filter=Filter(must=must_conditions),
        limit=top_k,
        with_payload=True,
    ).points

    return [
        {
            "text": r.payload["text"],
            "filename": r.payload["filename"],
            "document_id": r.payload["document_id"],
            "chunk_index": r.payload["chunk_index"],
            "score": r.score,
        }
        for r in results
    ]


# --- Delete Document Chunks ---

def delete_document_chunks(document_id: str, user_id: str):
    """
    Deletes all chunks belonging to a document.
    Filters by both document_id and user_id for safety.
    """
    client.delete(
        collection_name=settings.qdrant_collection,
        points_selector=Filter(
            must=[
                FieldCondition(
                    key="document_id",
                    match=MatchValue(value=document_id)
                ),
                FieldCondition(
                    key="user_id",
                    match=MatchValue(value=user_id)
                )
            ]
        )
    )