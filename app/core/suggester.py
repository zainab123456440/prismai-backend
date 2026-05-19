from groq import Groq
from openai import OpenAI
from app.config import settings
from typing import List

# --- Clients ---

groq_client = Groq(api_key=settings.groq_api_key)
openai_client = OpenAI(api_key=settings.openai_api_key)

# --- System Prompt ---

SUGGESTER_PROMPT = """You are a document analysis assistant.
Your job is to generate intelligent questions that a user
might want to ask about the provided document content.

Rules:
1. Generate exactly 5 questions
2. Questions must be specific to the document content
3. Questions should be genuinely useful and insightful
4. Mix different question types:
   - Factual questions (what, who, when, where)
   - Analytical questions (why, how)
   - Summary questions (what is the main point of...)
5. Return ONLY a JSON array of 5 strings
6. No numbering, no extra text, just the JSON array

Example output format:
["Question 1?", "Question 2?", "Question 3?", "Question 4?", "Question 5?"]"""


# --- Generate Suggested Questions ---

def generate_suggested_questions(
    text: str,
    filename: str = "",
) -> List[str]:
    """
    Generates 5 intelligent questions about
    the document content.
    Called once during ingestion after
    text is extracted.
    Uses first 3000 characters — enough
    context without wasting tokens.
    """

    # Use first 3000 chars for context
    # enough to understand the document
    context = text[:3000]

    user_prompt = f"""Document: {filename}

Content preview:
{context}

Generate 5 insightful questions a user
might want to ask about this document.
Return only a JSON array of 5 strings."""

    try:
        raw_response = call_llm(user_prompt)
        questions = parse_questions(raw_response)
        return questions

    except Exception:
        # If anything fails return safe defaults
        return get_default_questions(filename)


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
                    "content": SUGGESTER_PROMPT
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            temperature=0.7,
            max_tokens=300,
        )
        return response.choices[0].message.content

    else:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": SUGGESTER_PROMPT
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            temperature=0.7,
            max_tokens=300,
        )
        return response.choices[0].message.content


# --- Parse Response ---

def parse_questions(raw_response: str) -> List[str]:
    """
    Parses LLM response into a clean list of questions.
    Handles cases where LLM adds extra text
    around the JSON array.
    """
    import json
    import re

    # Find JSON array in response
    match = re.search(r'\[.*?\]', raw_response, re.DOTALL)

    if match:
        json_str = match.group(0)
        questions = json.loads(json_str)

        # Validate we got strings
        questions = [
            q for q in questions
            if isinstance(q, str) and len(q) > 10
        ]

        # Ensure exactly 5 questions
        return questions[:5]

    raise ValueError("Could not parse questions from response")


# --- Default Questions Fallback ---

def get_default_questions(filename: str) -> List[str]:
    """
    Safe fallback if LLM call fails.
    Generic but still useful questions.
    """
    name = filename.replace("_", " ").replace("-", " ")

    return [
        f"What is the main topic of {name}?",
        f"What are the key points covered in {name}?",
        f"What conclusions or findings are presented?",
        f"Who is the intended audience for this document?",
        f"What actions or next steps are recommended?",
    ]