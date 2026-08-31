"""
LinkedIn Search Worker (Live — Serper API)
==========================================
Fetches real LinkedIn job listings using the Serper Google Search API.

Flow:
  1. Build an optimized Google Search query scoped to linkedin.com/jobs
  2. Send to Serper → get organic results (title, link, snippet, date)
  3. Run Gemini enrichment on each result to extract:
     - Full job description (from snippet + Gemini inference)
     - Structured extractedRequirements list
     - Salary intelligence hints
  4. Return list of canonical Job dicts ready for ATS scoring

Falls back to a minimal set of sample data ONLY when Serper API key
is not configured (development mode).
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.gcp_clients import get_genai_client
from app.services.search.query_builder import SearchCriteria, build_serper_linkedin_query
from app.services.search.serper_client import (
    serper,
    normalize_result_to_job,
    extract_skills_from_text,
    parse_experience_from_text,
)

logger = logging.getLogger(__name__)


class LinkedInSearchWorker:
    """
    Live LinkedIn job search via Serper API + optional Gemini JD enrichment.
    """

    SOURCE = "LINKEDIN"

    def __init__(self):
        self._genai_client = None  # Lazy-init

    def _get_genai(self):
        if self._genai_client is None:
            self._genai_client = get_genai_client()
        return self._genai_client

    async def search_jobs(self, criteria: SearchCriteria) -> List[Dict[str, Any]]:
        """
        Main entry point: returns a list of live LinkedIn job dicts.
        """
        query = build_serper_linkedin_query(criteria)
        logger.info(f"[LinkedIn] Serper query: {query[:120]}")

        raw_results = await serper.search(
            query=query,
            num=settings.SERPER_MAX_RESULTS,
            country="in",
        )

        if not raw_results:
            logger.warning("[LinkedIn] Serper returned no results — check API key or query.")
            return []

        # Process results concurrently (max 8 at a time to avoid rate limits)
        sem = asyncio.Semaphore(8)
        tasks = [self._process_result(r, criteria, sem) for r in raw_results]
        jobs = await asyncio.gather(*tasks, return_exceptions=True)

        valid_jobs = []
        for j in jobs:
            if isinstance(j, dict) and j.get("jobId"):
                valid_jobs.append(j)
            elif isinstance(j, Exception):
                logger.debug(f"[LinkedIn] Result processing error: {j}")

        logger.info(f"[LinkedIn] Ingested {len(valid_jobs)} live listings.")
        return valid_jobs

    async def _process_result(
        self,
        result: Dict[str, Any],
        criteria: SearchCriteria,
        sem: asyncio.Semaphore,
    ) -> Optional[Dict[str, Any]]:
        """
        Convert a single Serper result into a canonical job dict.
        Optionally enriches with Gemini for structured requirement extraction.
        """
        async with sem:
            # Basic normalization
            job = normalize_result_to_job(result, self.SOURCE)

            # Skip non-job pages (e.g. LinkedIn profile pages, articles)
            url = job.get("externalUrl", "")
            if not any(kw in url for kw in ["/jobs/", "/job/", "jobs/view"]):
                return None

            # Gemini enrichment: extract structured requirements from snippet
            snippet = result.get("snippet", "")
            title = job.get("title", "")
            combined_text = f"{title}\n\n{snippet}"

            enriched_skills = await self._enrich_requirements_with_gemini(
                combined_text, criteria.required_skills
            )
            if enriched_skills:
                job["extractedRequirements"] = enriched_skills

            # Build basic salary intelligence from snippet signals
            job["salaryIntelligence"] = self._build_salary_intel(job, snippet)
            job["postedAt"] = result.get("date") or datetime.now(timezone.utc).isoformat()

            return job

    async def _enrich_requirements_with_gemini(
        self, text: str, user_skills: List[str]
    ) -> List[str]:
        """
        Use Gemini to extract a clean list of required skills from job text.
        Falls back to heuristic extraction if Gemini is unavailable.
        """
        client = self._get_genai()
        if not client or len(text.strip()) < 30:
            return extract_skills_from_text(text, user_skills)

        try:
            from google.genai import types

            prompt = f"""Extract a concise list of required technical skills, frameworks, and tools from this job posting text.
Return ONLY a JSON array of strings, maximum 10 items. Focus on technologies, not soft skills.
Example: ["Python", "FastAPI", "GCP", "PostgreSQL", "Kubernetes", "Docker"]

Job text:
{text[:800]}

JSON array:"""

            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.0,
                    max_output_tokens=200,
                ),
            )
            import json
            skills = json.loads(response.text)
            if isinstance(skills, list) and all(isinstance(s, str) for s in skills):
                return skills[:12]
        except Exception as e:
            logger.debug(f"[LinkedIn] Gemini enrichment skipped: {e}")

        return extract_skills_from_text(text, user_skills)

    def _build_salary_intel(self, job: Dict[str, Any], snippet: str) -> Dict[str, Any]:
        """Build salary intelligence for a LinkedIn job using snippet signals + market benchmarks."""
        from app.services.search.serper_client import parse_ctc_from_text, parse_experience_from_text

        company = job.get("companyName", "")
        title = job.get("title", "")
        combined = f"{title} {snippet}"

        min_ctc, max_ctc = parse_ctc_from_text(snippet)
        min_exp, max_exp = parse_experience_from_text(combined)

        # Market benchmark based on experience (Indian Tier-1 tech companies)
        mid_exp = ((min_exp or 3) + (max_exp or 6)) / 2
        benchmark_lpa = 18.0 + (mid_exp * 2.8)

        return {
            "company_name": company,
            "designation": title,
            "experience_bracket": f"{min_exp or 2}-{max_exp or 6} Years",
            "estimated_ctc_min_lpa": min_ctc or round(benchmark_lpa * 0.80, 1),
            "estimated_ctc_max_lpa": max_ctc or round(benchmark_lpa * 1.35, 1),
            "estimated_ctc_median_lpa": round(
                ((min_ctc or benchmark_lpa * 0.80) + (max_ctc or benchmark_lpa * 1.35)) / 2, 1
            ),
            "fixed_base_percentage": 80.0,
            "variable_pay_details": "10-15% annual performance bonus (standard Indian tech)",
            "esop_details": "ESOP/RSU grants common at product startups and unicorns",
            "ambitionbox_rating": 3.9,
            "glassdoor_rating": 3.8,
            "pros_summary": [
                "Live listing sourced directly from LinkedIn",
                "Real-time opportunity — apply early for best response rate",
            ],
            "cons_summary": ["Full compensation breakdown requires company-specific research"],
            "negotiation_leverage_tips": [
                "Always have 2+ competing offers before negotiating",
                "Ask for joining bonus to cover unvested equity from current employer",
                "Confirm if PF employer contribution is included in or outside the CTC",
            ],
        }
