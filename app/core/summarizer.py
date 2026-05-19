from groq import Groq
from openai import OpenAI
from app.config import settings

# --- Clients ---

groq_client = Groq(api_key=settings.groq_api_key)
openai_client = OpenAI(api_key=settings.openai_api_key)

# --- System Prompt ---

SUMMARIZER_PROMPT = """You are a document summarization assistant.
Your job is to create a clear and concise summary of documents.

Rules:
1. Write exactly 3-4 sentences
2. Cover the main topic and key points
3. Mention any important data, dates, or figures
4. Be factual — only what is in the document
5. Write in plain English — no jargon
6. Return ONLY the summary text
   No headings, no bullet points, no extra text"""


# --- Generate Summary ---

def generate_summary(
    text: str,
    filename: str = "",
) -> str:
    """
    Generates a 3-4 sentence summary of
    the document content.
    Called once during ingestion.
    Uses first 4000 characters for context.
    Summary is shown in document list so
    users know what each document contains
    without opening it.
    """

    # Use first 4000 chars
    # more context than suggester
    # for better summary quality
    context = text[:4000]

    user_prompt = f"""Document filename: {filename}

Content:
{context}

Write a 3-4 sentence summary of this document."""

    try:
        summary = call_llm(user_prompt)
        return summary.strip()

    except Exception:
        return get_default_summary(filename)


# --- LLM Call ---

def call_llm(user_prompt: str) -> str:
    """
    Calls Groq or OpenAI based on .env setting.
    """
    if settings.llm_provider == "groq":
        response = groq_client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {
                    "role": "system",
                    "content": SUMMARIZER_PROMPT
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            temperature=0.3,
            max_tokens=200,
        )
        return response.choices[0].message.content

    else:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": SUMMARIZER_PROMPT
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            temperature=0.3,
            max_tokens=200,
        )
        return response.choices[0].message.content


# --- Default Summary Fallback ---

def get_default_summary(filename: str) -> str:
    """
    Safe fallback if LLM call fails.
    Returns a simple message instead of crashing.
    """
    name = filename.replace("_", " ").replace("-", " ")
    return (
        f"{name} has been uploaded and processed successfully. "
        f"Ask questions to explore the content of this document."
    )