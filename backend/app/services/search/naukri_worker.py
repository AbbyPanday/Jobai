"""
Naukri Search Worker (Live — Serper API)
========================================
Fetches real Naukri.com job listings using Serper Google Search API.

Naukri snippets frequently contain CTC ranges and experience brackets,
making them especially valuable for salary intelligence enrichment.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.services.search.query_builder import SearchCriteria, build_serper_naukri_query
from app.services.search.serper_client import (
    serper,
    normalize_result_to_job,
    extract_skills_from_text,
    parse_ctc_from_text,
    parse_experience_from_text,
)

logger = logging.getLogger(__name__)


class NaukriSearchWorker:
    """
    Live Naukri job search via Serper API.
    Naukri is India's #1 job portal — snippets often include salary bands.
    """

    SOURCE = "NAUKRI"

    async def search_jobs(self, criteria: SearchCriteria) -> List[Dict[str, Any]]:
        """Main entry — returns list of live Naukri job dicts."""
        query = build_serper_naukri_query(criteria)
        logger.info(f"[Naukri] Serper query: {query[:120]}")

        raw_results = await serper.search(
            query=query,
            num=settings.SERPER_MAX_RESULTS,
            country="in",
        )

        if not raw_results:
            logger.warning("[Naukri] Serper returned no results.")
            return []

        sem = asyncio.Semaphore(8)
        tasks = [self._process_result(r, criteria, sem) for r in raw_results]
        jobs = await asyncio.gather(*tasks, return_exceptions=True)

        valid = [j for j in jobs if isinstance(j, dict) and j.get("jobId")]
        logger.info(f"[Naukri] Ingested {len(valid)} live listings.")
        return valid

    async def _process_result(
        self,
        result: Dict[str, Any],
        criteria: SearchCriteria,
        sem: asyncio.Semaphore,
    ) -> Optional[Dict[str, Any]]:
        async with sem:
            url = result.get("link", "")
            # Filter to actual Naukri job pages
            if "naukri.com" not in url:
                return None

            job = normalize_result_to_job(result, self.SOURCE)
            snippet = result.get("snippet", "")
            title = job.get("title", "")

            # Naukri snippets are often very informative — skip Gemini call
            # and rely on heuristic extraction (faster, no API cost)
            job["extractedRequirements"] = extract_skills_from_text(
                f"{title}\n{snippet}", criteria.required_skills
            )
            job["salaryIntelligence"] = self._build_naukri_salary_intel(job, snippet)
            job["postedAt"] = result.get("date") or datetime.now(timezone.utc).isoformat()
            return job

    def _build_naukri_salary_intel(
        self, job: Dict[str, Any], snippet: str
    ) -> Dict[str, Any]:
        """
        Naukri snippets frequently contain explicit CTC ranges.
        Parse them for maximum accuracy, fall back to benchmarks otherwise.
        """
        company = job.get("companyName", "")
        title = job.get("title", "")
        combined = f"{title} {snippet}"

        min_ctc, max_ctc = parse_ctc_from_text(snippet)
        min_exp, max_exp = parse_experience_from_text(combined)

        mid_exp = ((min_exp or 3) + (max_exp or 6)) / 2
        benchmark_lpa = 16.0 + (mid_exp * 2.5)

        return {
            "company_name": company,
            "designation": title,
            "experience_bracket": f"{min_exp or 2}-{max_exp or 6} Years",
            "estimated_ctc_min_lpa": min_ctc or round(benchmark_lpa * 0.80, 1),
            "estimated_ctc_max_lpa": max_ctc or round(benchmark_lpa * 1.30, 1),
            "estimated_ctc_median_lpa": round(
                ((min_ctc or benchmark_lpa * 0.80) + (max_ctc or benchmark_lpa * 1.30)) / 2, 1
            ),
            "fixed_base_percentage": 80.0,
            "variable_pay_details": "Performance bonus + retention (varies by company)",
            "esop_details": "ESOPs offered at funded startups and product companies",
            "ambitionbox_rating": 3.8,
            "glassdoor_rating": 3.7,
            "pros_summary": [
                "Naukri listing with direct apply option",
                "Salary range often listed explicitly on Naukri",
            ],
            "cons_summary": [
                "Some listings may be aggregated from third-party recruiters"
            ],
            "negotiation_leverage_tips": [
                "Naukri lists often have budget headroom — negotiate 15-20% above listed max",
                "Confirm CTC structure: gross vs net, PF inside or outside",
                "Reference competing Naukri / LinkedIn offers for leverage",
            ],
        }
