from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.config import settings
from app.api import auth, upload, query, documents, analytics
from app.db.qdrant import ensure_collection
import logging
import os
import uvicorn

# --- Logging Setup ---

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# --- Startup / Shutdown Events ---

@asynccontextmanager
async def lifespan(app: FastAPI):

    try:
        logger.info("🚀 PrismAI starting up...")
        logger.info(f"Environment: {settings.environment}")
        logger.info(f"LLM Provider: {settings.llm_provider}")

        ensure_collection()
        logger.info("✅ Qdrant collection ready")

        logger.info("✅ PrismAI initialized successfully")

    except Exception as e:
        logger.error(f"❌ Startup error: {e}")
        raise

    yield

    logger.info("🛑 PrismAI shutting down...")
    logger.info("✅ Cleanup complete")


# --- FastAPI App ---

app = FastAPI(
    title="PrismAI",
    description="Refract your documents into brilliant insights.",
    version="1.0.0",
    lifespan=lifespan,
)


# --- CORS Middleware ---

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://prismai-frontend-gs81.vercel.app",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

@app.middleware("http")
async def log_requests(request, call_next):
    print(f"🔥 Incoming request: {request.method} {request.url}")
    response = await call_next(request)
    print(f"   Response status: {response.status_code}")
    return response


# --- Health Endpoints ---

@app.get("/")
async def root():
    return {
        "name": "PrismAI",
        "tagline": "Refract your documents into brilliant insights.",
        "status": "running",
        "version": "1.0.0",
        "environment": settings.environment,
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "app": "PrismAI",
        "environment": settings.environment,
        "debug": settings.debug,
    }


# --- API Routers ---

app.include_router(auth.router, tags=["Authentication"])
app.include_router(upload.router, tags=["Upload"])
app.include_router(query.router, tags=["Query"])
app.include_router(documents.router, tags=["Documents"])
app.include_router(analytics.router, tags=["Analytics"])


# --- Run App ---

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
        reload=False,
        log_level="info",
    )