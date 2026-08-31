import os
from typing import List
from pydantic import BaseModel, Field

# Try loading .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

class Settings(BaseModel):
    PROJECT_NAME: str = "Autonomous Job Intelligence & Application Engine (India Focus)"
    API_V1_STR: str = "/api/v1"
    GCP_PROJECT_ID: str = Field(default_factory=lambda: os.getenv("GCP_PROJECT_ID", "local-dev-project"))
    GCP_REGION: str = Field(default_factory=lambda: os.getenv("GCP_REGION", "asia-south1"))

    # ── AI / Gemini ──────────────────────────────────────────────────────────
    GEMINI_API_KEY: str = Field(default_factory=lambda: os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "")
    GEMINI_MODEL: str = Field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))
    GEMINI_RESEARCH_MODEL: str = Field(default_factory=lambda: os.getenv("GEMINI_RESEARCH_MODEL", "gemini-2.5-flash"))
    GOOGLE_CLIENT_ID: str = Field(default_factory=lambda: os.getenv("GOOGLE_CLIENT_ID", ""))

    # ── Search APIs (SerpApi / Serper) ───────────────────────────────────────
    SERPAPI_API_KEY: str = Field(default_factory=lambda: os.getenv("SERPAPI_API_KEY") or os.getenv("SERPER_API_KEY", ""))
    SERPER_API_KEY: str = Field(default_factory=lambda: os.getenv("SERPER_API_KEY", ""))
    SERPER_BASE_URL: str = "https://google.serper.dev"
    SERPAPI_BASE_URL: str = "https://serpapi.com/search"
    # Maximum results fetched per source per search pass
    SERPER_MAX_RESULTS: int = Field(default_factory=lambda: int(os.getenv("SERPER_MAX_RESULTS", "20")))

    # ── LinkedOut Networking (A2A Job Discovery) ─────────────────────────────
    LINKEDOUT_BASE_URL: str = "https://www.linkedout.so"
    LINKEDOUT_API_KEY: str = Field(default_factory=lambda: os.getenv("LINKEDOUT_API_KEY", ""))
    LINKEDOUT_AGENT_HANDLE: str = Field(default_factory=lambda: os.getenv("LINKEDOUT_AGENT_HANDLE", ""))

    # ── Storage ──────────────────────────────────────────────────────────────
    GCS_BUCKET_NAME: str = Field(default_factory=lambda: os.getenv("GCS_BUCKET_NAME", "job-agent-artifacts"))
    FIRESTORE_COLLECTION_USERS: str = "users"
    FIRESTORE_COLLECTION_JOBS: str = "jobs"
    FIRESTORE_COLLECTION_APPLICATIONS: str = "applications"

    # ── CORS ─────────────────────────────────────────────────────────────────
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "*"
    ]

    # ── Matching ─────────────────────────────────────────────────────────────
    # Score threshold above which a job is flagged as "High Match" and queued for auto-apply
    DEFAULT_MATCH_THRESHOLD: float = 80.0
    # Salary research in-memory cache TTL in seconds (1 hour)
    SALARY_CACHE_TTL_SECONDS: int = 3600

settings = Settings()

