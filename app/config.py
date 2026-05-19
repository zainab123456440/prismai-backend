from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):

    # OpenAI
    openai_api_key: str

    # Groq
    groq_api_key: str
    llm_provider: str = "groq"
    llm_model: str = "llama3-70b-8192"
    embedding_model: str = "text-embedding-3-small"

    # Qdrant
    qdrant_url: str
    qdrant_api_key: str
    qdrant_collection: str = "prismai_documents"

    # Supabase
    supabase_url: str
    supabase_key: str

    # Redis
    redis_url: str

    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24

    # App
    app_name: str = "PrismAI"
    environment: str = "development"
    debug: bool = True
    max_file_size_mb: int = 20

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

# Single instance used everywhere
settings = Settings()