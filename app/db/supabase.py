from supabase import create_client, Client
from app.config import settings
from datetime import datetime
import uuid

# ================================
# SUPABASE CLIENT
# ================================

client: Client = create_client(
    settings.supabase_url,
    settings.supabase_key
)

# ================================
# USER FUNCTIONS
# ================================

def create_user(email: str, hashed_password: str, full_name: str) -> dict:
    """Creates a new user record in the public.users table."""
    
    try:
        data = {
            "email": email,
            "password": hashed_password,
            "full_name": full_name,
            "created_at": datetime.utcnow().isoformat()
        }

        result = client.table("users").insert(data).execute()

        if not result.data or len(result.data) == 0:
            raise Exception("Database insertion failed: No data returned.")

        return result.data[0]

    except Exception as e:
        print(f"❌ DATABASE ERROR in create_user: {str(e)}")
        raise Exception(str(e))


def get_user_by_email(email: str) -> dict | None:
    """Fetch user by email."""
    
    try:
        result = client.table("users").select("*").eq("email", email).execute()

        if result.data:
            return result.data[0]

        return None

    except Exception as e:
        print(f"❌ Error fetching user by email: {str(e)}")
        return None


def get_user_by_id(user_id: str) -> dict | None:
    """Fetch user by ID."""
    
    try:
        result = client.table("users").select("*").eq("id", user_id).execute()

        if result.data:
            return result.data[0]

        return None

    except Exception as e:
        print(f"❌ Error fetching user by ID: {str(e)}")
        return None


# ================================
# DOCUMENT FUNCTIONS
# ================================

def create_document_record(
    document_id: str,
    user_id: str,
    filename: str,
    file_type: str,
    status: str = "queued"
) -> dict:

    try:
        data = {
            "id": document_id,
            "user_id": user_id,
            "filename": filename,
            "file_type": file_type,
            "status": status,
            "chunk_count": 0,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }

        result = client.table("documents").insert(data).execute()

        return result.data[0]

    except Exception as e:
        print(f"❌ Error in create_document_record: {str(e)}")
        raise


def update_document_status(
    document_id: str,
    status: str,
    chunk_count: int = None
):

    try:
        update_data = {
            "status": status,
            "updated_at": datetime.utcnow().isoformat()
        }

        if chunk_count is not None:
            update_data["chunk_count"] = chunk_count

        client.table("documents").update(update_data).eq(
            "id",
            document_id
        ).execute()

    except Exception as e:
        print(f"❌ Error updating document status: {str(e)}")


def get_document_status(document_id: str) -> dict | None:
    """Get document status."""
    
    try:
        result = client.table("documents").select("*").eq(
            "id",
            document_id
        ).execute()

        if result.data:
            return result.data[0]

        return None

    except Exception as e:
        print(f"❌ Error in get_document_status: {str(e)}")
        return None


def get_user_documents(user_id: str) -> list[dict]:
    """Get all documents of a user."""

    try:
        result = client.table("documents").select("*").eq(
            "user_id",
            user_id
        ).order(
            "created_at",
            desc=True
        ).execute()

        return result.data

    except Exception as e:
        print(f"❌ Error in get_user_documents: {str(e)}")
        return []


def delete_document_record(document_id: str, user_id: str):
    """Delete a document."""

    try:
        client.table("documents").delete().eq(
            "id",
            document_id
        ).eq(
            "user_id",
            user_id
        ).execute()

    except Exception as e:
        print(f"❌ Error deleting document: {str(e)}")


def save_document_summary(document_id: str, summary: str):
    """Save generated document summary."""

    try:
        client.table("documents").update({
            "summary": summary
        }).eq(
            "id",
            document_id
        ).execute()

    except Exception as e:
        print(f"❌ Error saving summary: {str(e)}")


def save_suggested_questions(document_id: str, questions: list[str]):
    """Save suggested questions."""

    try:
        client.table("documents").update({
            "suggested_questions": questions
        }).eq(
            "id",
            document_id
        ).execute()

    except Exception as e:
        print(f"❌ Error saving suggested questions: {str(e)}")


# ================================
# QUERY / ANALYTICS FUNCTIONS
# ================================

def log_query(
    user_id: str,
    question: str,
    answer: str,
    document_id: str = None,
    response_time_ms: int = 0
):

    try:
        data = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "question": question,
            "answer": answer,
            "document_id": document_id,
            "response_time_ms": response_time_ms,
            "created_at": datetime.utcnow().isoformat()
        }

        client.table("queries").insert(data).execute()

    except Exception as e:
        print(f"❌ Error logging query: {str(e)}")


def get_queries_per_day(user_id: str) -> list[dict]:
    """Get queries grouped per day."""

    try:
        result = client.rpc(
            "get_queries_per_day",
            {"p_user_id": user_id}
        ).execute()

        return result.data

    except Exception as e:
        print(f"❌ Error getting daily queries: {str(e)}")
        return []


def get_top_documents(user_id: str) -> list[dict]:
    """Get top documents."""

    try:
        result = client.rpc(
            "get_top_documents",
            {"p_user_id": user_id}
        ).execute()

        return result.data

    except Exception as e:
        print(f"❌ Error getting top documents: {str(e)}")
        return []


def get_query_history(user_id: str, limit: int = 50) -> list[dict]:
    """Get query history."""

    try:
        result = client.table("queries").select("*").eq(
            "user_id",
            user_id
        ).order(
            "created_at",
            desc=True
        ).limit(limit).execute()

        return result.data

    except Exception as e:
        print(f"❌ Error fetching query history: {str(e)}")
        return []


def get_dashboard_summary(user_id: str) -> dict:
    """Get dashboard analytics summary."""

    try:
        docs = client.table("documents").select(
            "id, status"
        ).eq(
            "user_id",
            user_id
        ).execute()

        total_documents = len(docs.data)

        documents_ready = len([
            d for d in docs.data
            if d.get("status") == "ready"
        ])

        documents_processing = len([
            d for d in docs.data
            if d.get("status") == "processing"
        ])

        queries = client.table("queries").select(
            "id, response_time_ms, created_at"
        ).eq(
            "user_id",
            user_id
        ).execute()

        total_queries = len(queries.data)

        avg_response_time = (
            sum(
                q.get("response_time_ms", 0)
                for q in queries.data
            ) // total_queries
            if total_queries > 0
            else 0
        )

        today = datetime.utcnow().date().isoformat()

        queries_today = len([
            q for q in queries.data
            if q.get("created_at", "").startswith(today)
        ])

        return {
            "total_documents": total_documents,
            "total_queries": total_queries,
            "avg_response_time_ms": avg_response_time,
            "queries_today": queries_today,
            "documents_ready": documents_ready,
            "documents_processing": documents_processing,
        }

    except Exception as e:
        print(f"❌ Error in get_dashboard_summary: {str(e)}")

        return {
            "total_documents": 0,
            "total_queries": 0,
            "avg_response_time_ms": 0,
            "queries_today": 0,
            "documents_ready": 0,
            "documents_processing": 0
        }