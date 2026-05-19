from app.core.embedder import embed_query
from app.db.qdrant import search_chunks
from typing import List


def retrieve_chunks(
    question: str,
    user_id: str,
    document_id: str = None,
    top_k: int = 5,
) -> List[dict]:

    # Step 1 — Embed the question
    query_embedding = embed_query(question)

    # Step 2 — Search Qdrant for similar chunks
    chunks = search_chunks(
        query_embedding=query_embedding,
        user_id=user_id,
        document_id=document_id,
        top_k=top_k,
    )

    # Debug — see what Qdrant returned
    print(f"🔍 Raw chunks from Qdrant: {len(chunks)}")
    for c in chunks:
        print(f"   score: {c['score']:.3f} — {c['filename']}")

    # Step 3 — Filter low quality results
    # 0.1 is very permissive — returns almost everything
    chunks = [
        chunk for chunk in chunks
        if chunk["score"] >= 0.1
    ]

    print(f"✅ Chunks after filter: {len(chunks)}")

    return chunks


def retrieve_with_context(
    question: str,
    user_id: str,
    document_id: str = None,
    top_k: int = 10,  # increased from 5 to get more context
) -> dict:

    chunks = retrieve_chunks(
        question=question,
        user_id=user_id,
        document_id=document_id,
        top_k=top_k,
    )

    # No chunks — still return has_context True for general chat
    # so the LLM can respond naturally to greetings etc.
    if not chunks:
        return {
            "context": "No specific document context found.",
            "chunks": [],
            "has_context": True,  # ← let LLM handle it gracefully
        }

    context_parts = []

    for i, chunk in enumerate(chunks, start=1):
        context_parts.append(
            f"[Source {i} — {chunk['filename']}]\n"
            f"{chunk['text']}\n"
        )

    context = "\n---\n".join(context_parts)

    return {
        "context": context,
        "chunks": chunks,
        "has_context": True,
    }