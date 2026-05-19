from openai import OpenAI
from app.config import settings
from typing import List

# --- Client ---

client = OpenAI(api_key=settings.openai_api_key)

# --- Embed Multiple Chunks ---

def embed_chunks(chunks: List[str]) -> List[List[float]]:
    """
    Generates embeddings for a list of chunks.
    Called during document ingestion.
    Processes in batches of 100 to avoid
    hitting OpenAI API limits.
    """
    all_embeddings = []
    batch_size = 100

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]

        response = client.embeddings.create(
            model=settings.embedding_model,
            input=batch,
        )

        batch_embeddings = [
            item.embedding for item in response.data
        ]
        all_embeddings.extend(batch_embeddings)

    return all_embeddings


# --- Embed Single Query ---

def embed_query(query: str) -> List[float]:
    """
    Generates embedding for a single query.
    Called at query time when user asks a question.
    """
    response = client.embeddings.create(
        model=settings.embedding_model,
        input=[query],
    )

    return response.data[0].embedding