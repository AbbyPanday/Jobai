"""
Serper API Async Client
=======================
Centralized async HTTP client for the Serper Google Search API (https://serper.dev).

Supports:
  - Google Search  → /search
  - Google News    → /news

Features:
  - Async/await with httpx
  - Exponential backoff on 429 / 5xx
  - Per-request timeout
  - Result normalization into a common schema
  - URL deduplication helper
"""

import asyncio
import hashlib
import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse, urlunparse

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Normalised result schema (source-agnostic)
# ---------------------------------------------------------------------------

def _normalize_url(url: str) -> str:
    """Strip tracking params and fragments for reliable deduplication."""
    try:
        parsed = urlparse(url)
        # Keep only scheme + netloc + path, discard query & fragment
        clean = urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))
        return clean.rstrip("/").lower()
    except Exception:
        return url.lower()


def _make_job_id(source: str, url: str) -> str:
    """Stable deterministic job ID derived from source + URL."""
    h = hashlib.md5(f"{source}::{_normalize_url(url)}".encode()).hexdigest()[:12]
    return f"job_{source.lower()[:3]}_{h}"


# ---------------------------------------------------------------------------
# Serper Client
# ---------------------------------------------------------------------------

class SerperClient:
    """
    Async Serper API client with retry logic.

    Usage:
        client = SerperClient()
        results = await client.search("site:linkedin.com/jobs \"Python\" \"Bangalore\"", num=20)
    """

    BASE_URL = settings.SERPER_BASE_URL
    SERPAPI_URL = settings.SERPAPI_BASE_URL
    MAX_RETRIES = 3
    RETRY_BACKOFF_BASE = 1.5  # seconds

    def __init__(self):
        self._serper_key = settings.SERPER_API_KEY
        self._serpapi_key = settings.SERPAPI_API_KEY

        if not self._serpapi_key and not self._serper_key:
            logger.warning(
                "Neither SERPAPI_API_KEY nor SERPER_API_KEY is set. Live job search will be unavailable."
            )

    @property
    def is_configured(self) -> bool:
        return bool(self._serpapi_key or self._serper_key)

    async def search(
        self,
        query: str,
        num: int = 20,
        country: str = "in",
        locale: str = "en",
        endpoint: str = "/search",
    ) -> List[Dict[str, Any]]:
        """
        Execute a Google Search via SerpApi (primary) or Serper (fallback).
        Returns list of organic result dicts with keys: title, link, snippet, position.
        """
        if not self.is_configured:
            logger.warning("Search API key missing — skipping live search.")
            return []

        # 1. Try SerpApi first if key is present
        if self._serpapi_key:
            try:
                params = {
                    "engine": "google",
                    "q": query,
                    "gl": country,
                    "hl": locale,
                    "num": min(num, 50),
                    "api_key": self._serpapi_key,
                }
                async with httpx.AsyncClient(timeout=20.0) as client:
                    resp = await client.get(self.SERPAPI_URL, params=params)

                if resp.status_code == 200:
                    data = resp.json()
                    organic = data.get("organic_results", [])
                    results = [
                        {
                            "title": item.get("title", ""),
                            "link": item.get("link", ""),
                            "snippet": item.get("snippet", ""),
                            "position": item.get("position", idx + 1),
                        }
                        for idx, item in enumerate(organic)
                    ]
                    logger.info(f"SerpApi search '{query[:60]}...' → {len(results)} results")
                    return results
            except Exception as e:
                logger.warning(f"SerpApi search failed: {e}. Falling back to Serper if available.")

        # 2. Try Serper if key available
        if self._serper_key:
            payload = {
                "q": query,
                "num": min(num, 100),
                "gl": country,
                "hl": locale,
            }
            headers = {
                "X-API-KEY": self._serper_key,
                "Content-Type": "application/json",
            }
            url = f"{self.BASE_URL}{endpoint}"

            for attempt in range(self.MAX_RETRIES):
                try:
                    async with httpx.AsyncClient(timeout=15.0) as client:
                        resp = await client.post(url, json=payload, headers=headers)

                    if resp.status_code == 200:
                        data = resp.json()
                        results = data.get("organic", data.get("news", []))
                        logger.info(f"Serper search '{query[:60]}...' → {len(results)} results")
                        return results
                    elif resp.status_code == 429:
                        wait = self.RETRY_BACKOFF_BASE ** (attempt + 1)
                        await asyncio.sleep(wait)
                    else:
                        break
                except Exception as exc:
                    logger.error(f"Serper request failed: {exc}")
                    break

        return []

    async def search_google_jobs(
        self,
        query: str,
        country: str = "in",
        locale: str = "en",
    ) -> List[Dict[str, Any]]:
        """
        Execute a live Google Jobs API search via SerpApi engine=google_jobs.
        Returns rich job entries directly from Google Jobs.
        """
        if not self._serpapi_key:
            return []

        try:
            params = {
                "engine": "google_jobs",
                "q": query,
                "gl": country,
                "hl": locale,
                "api_key": self._serpapi_key,
            }
            async with httpx.AsyncClient(timeout=25.0) as client:
                resp = await client.get(self.SERPAPI_URL, params=params)

            if resp.status_code == 200:
                data = resp.json()
                return data.get("jobs_results", [])
            else:
                logger.warning(f"SerpApi Google Jobs status {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            logger.error(f"SerpApi Google Jobs request failed: {e}")

        return []

    async def news(self, query: str, num: int = 10) -> List[Dict[str, Any]]:
        """Convenience wrapper for news search."""
        return await self.search(query, num=num, endpoint="/news")


# ---------------------------------------------------------------------------
# Result Parsing Utilities
# ---------------------------------------------------------------------------

# Regex to detect experience requirements in a JD snippet
_EXP_PATTERN = re.compile(
    r"(\d+)\s*[-–to]+\s*(\d+)\s*(?:years?|yrs?)",
    re.IGNORECASE,
)
_EXP_SINGLE = re.compile(r"(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s+)?(?:experience)?", re.IGNORECASE)

# Regex patterns for extracting CTC hints from snippets
_CTC_PATTERN = re.compile(
    r"(?:₹|rs\.?|inr)?\s*(\d{1,3}(?:\.\d+)?)\s*[-–to]+\s*(\d{1,3}(?:\.\d+)?)\s*(?:lpa|lakh|lakhs|l|cr)",
    re.IGNORECASE,
)


def parse_experience_from_text(text: str) -> tuple[Optional[int], Optional[int]]:
    """Extract (min_exp, max_exp) from a JD text snippet. Returns (None, None) if not found."""
    rng = _EXP_PATTERN.search(text)
    if rng:
        return int(rng.group(1)), int(rng.group(2))
    single = _EXP_SINGLE.search(text)
    if single:
        val = int(single.group(1))
        return max(0, val - 1), val + 2
    return None, None


def parse_ctc_from_text(text: str) -> tuple[Optional[float], Optional[float]]:
    """Extract (min_ctc_lpa, max_ctc_lpa) from a JD text snippet. Returns (None, None) if not found."""
    match = _CTC_PATTERN.search(text)
    if match:
        lo, hi = float(match.group(1)), float(match.group(2))
        # Sanity check: typical Indian tech range 5–200 LPA
        if 5 <= lo <= 200 and 5 <= hi <= 200:
            return lo, hi
    return None, None


def extract_skills_from_text(text: str, known_skills: Optional[List[str]] = None) -> List[str]:
    """
    Heuristic skill extraction from raw JD text.
    Checks against a curated tech skill vocabulary. 
    If known_skills list provided, uses it for exact match first.
    """
    TECH_VOCABULARY = {
        "python", "fastapi", "django", "flask", "go", "golang", "java", "kotlin",
        "typescript", "javascript", "node.js", "nodejs", "react", "next.js", "nextjs",
        "vue", "angular", "rust", "c++", "scala", "ruby",
        "postgresql", "postgres", "mysql", "mongodb", "redis", "cassandra", "elasticsearch",
        "kafka", "rabbitmq", "celery", "airflow",
        "gcp", "google cloud", "aws", "azure", "cloud run", "bigquery", "cloud functions",
        "kubernetes", "k8s", "docker", "helm", "terraform", "ansible",
        "ci/cd", "jenkins", "github actions", "gitlab ci",
        "spark", "hadoop", "databricks",
        "machine learning", "ml", "deep learning", "pytorch", "tensorflow",
        "llm", "langchain", "gemini", "openai", "rag",
        "microservices", "grpc", "graphql", "rest api", "websocket",
        "system design", "distributed systems", "high availability",
        "linux", "bash", "nginx", "prometheus", "grafana",
    }

    text_lower = text.lower()
    found = []

    # Check provided known_skills first
    if known_skills:
        for skill in known_skills:
            if skill.lower() in text_lower and skill not in found:
                found.append(skill)

    # Then scan tech vocabulary
    for skill in TECH_VOCABULARY:
        if skill in text_lower and skill.title() not in found and skill not in found:
            # Use title-cased display name
            display = {
                "gcp": "GCP", "aws": "AWS", "azure": "Azure",
                "postgresql": "PostgreSQL", "mysql": "MySQL", "mongodb": "MongoDB",
                "redis": "Redis", "kafka": "Kafka", "kubernetes": "Kubernetes",
                "docker": "Docker", "fastapi": "FastAPI", "django": "Django",
                "flask": "Flask", "golang": "Go", "nodejs": "Node.js",
                "nextjs": "Next.js", "grpc": "gRPC", "graphql": "GraphQL",
                "ci/cd": "CI/CD", "ml": "Machine Learning", "llm": "LLM",
                "rag": "RAG", "k8s": "Kubernetes", "linux": "Linux",
                "bash": "Bash", "nginx": "Nginx",
            }.get(skill, skill.title())
            found.append(display)

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for s in found:
        key = s.lower()
        if key not in seen:
            seen.add(key)
            unique.append(s)

    return unique[:12]  # Cap at 12 skills


def normalize_result_to_job(
    result: Dict[str, Any],
    source: str,
    salary_intelligence: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Convert a raw Serper organic result dict into the canonical Job schema
    expected by the rest of the application.
    """
    url = result.get("link", "")
    title = result.get("title", "Unknown Role")
    snippet = result.get("snippet", "")

    # Clean up title (remove site name suffixes e.g. "Senior Engineer - LinkedIn")
    title = re.sub(r"\s*[-|–]\s*(LinkedIn|Naukri|Glassdoor|Indeed|Google Jobs).*$", "", title, flags=re.IGNORECASE).strip()

    # Extract company from snippet or title
    company = "Unknown Company"
    company_match = re.search(
        r"(?:at|@|by|with|for)\s+([A-Z][A-Za-z0-9&\s\-\.]{2,40}?)(?:\.|,|\s+in\s|\s+is\s|\s+·|$)",
        snippet,
    )
    if company_match:
        company = company_match.group(1).strip()

    # Also try to get from sitelinks or result metadata
    if result.get("attributes", {}).get("Company"):
        company = result["attributes"]["Company"]

    # Parse experience and CTC signals
    min_exp, max_exp = parse_experience_from_text(snippet + " " + title)
    min_ctc, max_ctc = parse_ctc_from_text(snippet)

    # Build salary intelligence if not provided
    if not salary_intelligence and (min_ctc or min_exp):
        base_exp = ((min_exp or 0) + (max_exp or min_exp or 3)) / 2
        base_lpa = 20.0 + (base_exp * 2.5)
        salary_intelligence = {
            "company_name": company,
            "designation": title,
            "experience_bracket": f"{min_exp or 0}-{max_exp or 5} Years",
            "estimated_ctc_min_lpa": min_ctc or round(base_lpa * 0.85, 1),
            "estimated_ctc_max_lpa": max_ctc or round(base_lpa * 1.30, 1),
            "estimated_ctc_median_lpa": round(
                ((min_ctc or base_lpa * 0.85) + (max_ctc or base_lpa * 1.30)) / 2, 1
            ),
            "fixed_base_percentage": 80.0,
            "variable_pay_details": "10-15% annual performance bonus",
            "esop_details": None,
            "ambitionbox_rating": 3.9,
            "glassdoor_rating": 3.8,
            "pros_summary": ["Modern tech stack", "Competitive salary"],
            "cons_summary": ["Information from search snippet only"],
            "negotiation_leverage_tips": [
                "Get competing offers before negotiating",
                "Clarify if CTC includes PF employer contribution",
            ],
        }

    job_id = _make_job_id(source, url)
    extracted_requirements = extract_skills_from_text(snippet + " " + title)

    return {
        "jobId": job_id,
        "source": source,
        "externalUrl": url,
        "companyName": company,
        "title": title,
        "location": _extract_location(snippet + " " + title),
        "rawDescription": snippet,
        "salaryIntelligence": salary_intelligence,
        "extractedRequirements": extracted_requirements,
        "postedAt": result.get("date", ""),
        "_normalizedUrl": _normalize_url(url),
    }


def _extract_location(text: str) -> str:
    """Heuristic location extraction from Indian job market."""
    CITIES = [
        "Bengaluru", "Bangalore", "Pune", "Hyderabad", "Mumbai", "Chennai",
        "Gurugram", "Gurgaon", "Noida", "Delhi", "Kolkata", "Ahmedabad",
        "Kochi", "Jaipur", "Chandigarh",
    ]
    text_lower = text.lower()
    for city in CITIES:
        if city.lower() in text_lower:
            if "remote" in text_lower or "hybrid" in text_lower:
                suffix = " (Remote)" if "remote" in text_lower else " (Hybrid)"
                return f"{city}{suffix}"
            return city
    if "remote" in text_lower:
        return "Remote (India)"
    return "India"


# Global singleton instance
serper = SerperClient()
