import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.api.routes_jobs import router as jobs_router
from app.api.routes_applications import router as applications_router
from app.api.routes_profile import router as profile_router
from app.api.routes_auth import router as auth_router
from app.api.routes_integrations import router as integrations_router
from app.api.routes_networking import router as networking_router
from app.api.websocket_agent import ws_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Autonomous Job Intelligence & Application Engine (India Focus)...")
    logger.info(f"Using Gemini Model: {settings.GEMINI_MODEL}")
    logger.info("Local In-Memory / Firestore Persistence active.")
    yield
    logger.info("Shutting down engine...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Production-grade AI-native job intelligence, compensation research, and autonomous application engine for the Indian tech market.",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(jobs_router, prefix=settings.API_V1_STR)
app.include_router(applications_router, prefix=settings.API_V1_STR)
app.include_router(profile_router, prefix=settings.API_V1_STR)
app.include_router(integrations_router, prefix=settings.API_V1_STR)
app.include_router(networking_router, prefix=settings.API_V1_STR)
app.include_router(ws_router)

@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "region": settings.GCP_REGION,
        "version": "1.0.0"
    }

@app.get("/", tags=["System"])
async def root():
    return {
        "message": "Next-Gen Autonomous Job Intelligence & Application Engine API Gateway",
        "docs": "/docs",
        "wsEndpoint": "/ws/agent-feed/{user_id}"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
