from groq import Groq
from openai import OpenAI
from app.config import settings
from app.core.retriever import retrieve_with_context
from typing import List
import time

# --- Clients ---

groq_client = Groq(api_key=settings.groq_api_key)
openai_client = OpenAI(api_key=settings.openai_api_key)

# --- System Prompt ---

SYSTEM_PROMPT = SYSTEM_PROMPT = SYSTEM_PROMPT = """You are PrismAI, a friendly and intelligent document assistant.

Rules:
1. If the user sends a greeting or general message (like "hello", "thanks", "how are you"),
   respond warmly and naturally — no need to mention documents.
2. If the context contains relevant information, answer from it and cite the filename.
3. If the context says "No specific document context found" and the user asked a real
   question, say you could not find that information and suggest rephrasing.
4. Never make up information not present in the context.
5. Be concise, friendly and helpful at all times.
"""


# --- Main Generate Function ---

def generate_answer(
    question: str,
    user_id: str,
    document_id: str = None,
    top_k: int = 5,
) -> dict:
    """
    Full RAG pipeline in one function.
    Retrieves context then generates answer.
    Returns answer, citations and response time.
    """

    start_time = time.time()

    # Step 1 — Retrieve relevant chunks
    retrieval_result = retrieve_with_context(
        question=question,
        user_id=user_id,
        document_id=document_id,
        top_k=top_k,
    )

    # Step 2 — Handle no context found
    if not retrieval_result["has_context"]:
        return {
            "answer": "I could not find relevant information in your documents. Please make sure your documents are fully processed and try rephrasing your question.",
            "citations": [],
            "response_time_ms": int(
                (time.time() - start_time) * 1000
            ),
        }

    context = retrieval_result["context"]
    chunks = retrieval_result["chunks"]

    # Step 3 — Build prompt
    user_prompt = f"""Context from documents:
{context}

Question: {question}

Answer based only on the context above:"""

    # Step 4 — Call LLM
    answer = call_llm(user_prompt)

    # Step 5 — Build citations
    citations = build_citations(chunks)

    # Step 6 — Calculate response time
    response_time_ms = int((time.time() - start_time) * 1000)

    return {
        "answer": answer,
        "citations": citations,
        "response_time_ms": response_time_ms,
    }


# --- LLM Call ---

def call_llm(user_prompt: str) -> str:
    """
    Calls either Groq or OpenAI based on
    LLM_PROVIDER setting in .env.
    Switch providers by changing one line in .env.
    """

    if settings.llm_provider == "groq":
        return call_groq(user_prompt)
    else:
        return call_openai(user_prompt)


def call_groq(user_prompt: str) -> str:
    """
    Calls Groq LLM — fast and free.
    Default provider for PrismAI.
    """
    response = groq_client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        temperature=0.1,
        max_tokens=1000,
    )

    return response.choices[0].message.content


def call_openai(user_prompt: str) -> str:
    """
    Calls OpenAI LLM — fallback provider.
    Used when Groq is unavailable or
    LLM_PROVIDER=openai in .env
    """
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        temperature=0.1,
        max_tokens=1000,
    )

    return response.choices[0].message.content


# --- Build Citations ---

def build_citations(chunks: List[dict]) -> List[dict]:
    """
    Converts raw chunks into clean citation objects.
    Removes duplicate sources.
    """
    seen = set()
    citations = []

    for chunk in chunks:
        # Avoid duplicate citations from same chunk
        key = f"{chunk['filename']}_{chunk['chunk_index']}"
        if key in seen:
            continue

        seen.add(key)
        citations.append({
            "filename": chunk["filename"],
            "chunk_text": chunk["text"][:300] + "..."
            if len(chunk["text"]) > 300
            else chunk["text"],
            "relevance_score": round(chunk["score"], 3),
            "chunk_index": chunk["chunk_index"],
        })

    return citations
