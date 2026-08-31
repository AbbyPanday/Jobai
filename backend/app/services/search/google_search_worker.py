"""
Google Discovery Search Worker (Live — Serper API + Gemini Grounding)
======================================================================
Discovers jobs from:
  - Greenhouse.io, Lever.co, Workday career portals
  - Direct company career pages
  - LinkedIn hiring manager posts (off-market roles)

This complements LinkedIn/Naukri with unlisted and freshly-posted positions
that haven't been indexed on major job boards yet.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.gcp_clients import get_genai_client
from app.services.search.query_builder import (
    SearchCriteria,
    build_serper_google_discovery_query,
    build_serper_hiring_manager_query,
)
from app.services.search.serper_client import (
    serper,
    normalize_result_to_job,
    extract_skills_from_text,
    parse_experience_from_text,
)

logger = logging.getLogger(__name__)

# ATS portal domains we recognize as valid job portals
KNOWN_PORTAL_DOMAINS = {
    "boards.greenhouse.io": "Greenhouse",
    "lever.co": "Lever",
    "jobs.lever.co": "Lever",
    "myworkdayjobs.com": "Workday",
    "jobs.smartrecruiters.com": "SmartRecruiters",
    "careers.google.com": "Google Careers",
    "amazon.jobs": "Amazon Jobs",
    "microsoft.com/careers": "Microsoft",
    "apply.workable.com": "Workable",
    "in.linkedin.com": "LinkedIn",
    "linkedin.com": "LinkedIn",
}


class GoogleSearchWorker:
    """
    Live discovery of off-market and freshly-posted tech jobs via Serper.
    Uses both portal-targeted search and Gemini Google Search Grounding.
    """

    SOURCE = "GOOGLE_SEARCH"

    def __init__(self):
        self._genai_client = None

    def _get_genai(self):
        if self._genai_client is None:
            self._genai_client = get_genai_client()
        return self._genai_client

    async def search_jobs(self, criteria: SearchCriteria) -> List[Dict[str, Any]]:
        """
        Runs two parallel sub-searches:
        1. ATS portal discovery (Greenhouse, Lever, Workday)
        2. Hiring manager post discovery (LinkedIn posts with "hiring")
        Also attempts Gemini Search Grounding if API key is set.
        """
        portal_query = build_serper_google_discovery_query(criteria)
        hiring_query = build_serper_hiring_manager_query(criteria)
        role = criteria.titles[0] if criteria.titles else "Software Engineer"
        skill = criteria.required_skills[0] if criteria.required_skills else "Python"
        loc = criteria.locations[0] if criteria.locations else "Bengaluru"
        jobs_query = f"{role} {skill} {loc}"

        logger.info(f"[Google] Portal query: {portal_query[:100]}")
        logger.info(f"[Google] Google Jobs query: {jobs_query}")

        # Run portal search + hiring manager search + Google Jobs API in parallel
        portal_results, hiring_results, google_jobs_raw = await asyncio.gather(
            serper.search(portal_query, num=min(settings.SERPER_MAX_RESULTS, 15), country="in"),
            serper.search(hiring_query, num=10, country="in"),
            serper.search_google_jobs(jobs_query, country="in"),
            return_exceptions=True,
        )

        all_raw = []
        if isinstance(portal_results, list):
            all_raw.extend(portal_results)
        if isinstance(hiring_results, list):
            all_raw.extend(hiring_results)

        # Convert google_jobs_raw into common format if returned
        if isinstance(google_jobs_raw, list):
            for gj in google_jobs_raw:
                apply_links = gj.get("apply_options", [])
                apply_url = apply_links[0].get("link") if apply_links else f"https://www.google.com/search?q={jobs_query}"
                all_raw.append({
                    "title": gj.get("title", ""),
                    "link": apply_url,
                    "snippet": f"{gj.get('company_name', '')} - {gj.get('location', '')}. {gj.get('description', '')[:200]}",
                    "company": gj.get("company_name", ""),
                    "location": gj.get("location", ""),
                })

        if not all_raw:
            logger.warning("[Google] No results from either sub-search.")
            # Try Gemini grounding as final fallback
            return await self._try_gemini_grounding(criteria)

        sem = asyncio.Semaphore(8)
        tasks = [self._process_result(r, criteria, sem) for r in all_raw]
        jobs = await asyncio.gather(*tasks, return_exceptions=True)

        valid = [j for j in jobs if isinstance(j, dict) and j.get("jobId")]
        logger.info(f"[Google] Ingested {len(valid)} live discovery listings.")
        return valid

    async def _process_result(
        self,
        result: Dict[str, Any],
        criteria: SearchCriteria,
        sem: asyncio.Semaphore,
    ) -> Optional[Dict[str, Any]]:
        async with sem:
            url = result.get("link", "")
            snippet = result.get("snippet", "")
            title = result.get("title", "")

            # Detect portal type from URL
            portal_name = self._detect_portal(url)

            job = normalize_result_to_job(result, self.SOURCE)
            job["extractedRequirements"] = extract_skills_from_text(
                f"{title}\n{snippet}", criteria.required_skills
            )
            job["salaryIntelligence"] = self._build_salary_intel(job, snippet, criteria)
            job["postedAt"] = result.get("date") or datetime.now(timezone.utc).isoformat()
            if portal_name:
                job["portalType"] = portal_name

            return job

    def _detect_portal(self, url: str) -> Optional[str]:
        """Identify the ATS portal from URL domain."""
        url_lower = url.lower()
        for domain, name in KNOWN_PORTAL_DOMAINS.items():
            if domain in url_lower:
                return name
        return None

    async def _try_gemini_grounding(self, criteria: SearchCriteria) -> List[Dict[str, Any]]:
        """
        Fallback: use Gemini with Google Search Grounding to discover jobs.
        Only fires if Serper returns nothing.
        """
        client = self._get_genai()
        if not client:
            return []

        try:
            from google.genai import types
            from app.services.search.query_builder import build_google_grounding_query
            import json

            grounding_query = build_google_grounding_query(criteria)
            prompt = f"""Search and find 3 recent software engineering jobs in India matching:
Query: {grounding_query}
Required skills: {', '.join(criteria.required_skills)}
Experience: {criteria.min_exp_years}-{criteria.max_exp_years} years.
Return JSON array with fields: companyName, title, location, externalUrl, rawDescription, extractedRequirements (array of strings).
"""
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[{"google_search": {}}],
                    temperature=0.2,
                ),
            )
            text = response.text.strip()
            # Extract JSON array from response
            import re
            json_match = re.search(r'\[.*\]', text, re.DOTALL)
            if json_match:
                raw_jobs = json.loads(json_match.group(0))
                results = []
                for rj in raw_jobs[:3]:
                    from app.services.search.serper_client import _make_job_id
                    url = rj.get("externalUrl", "")
                    results.append({
                        "jobId": _make_job_id(self.SOURCE, url or rj.get("title", "")),
                        "source": self.SOURCE,
                        "externalUrl": url,
                        "companyName": rj.get("companyName", "Unknown"),
                        "title": rj.get("title", "Software Engineer"),
                        "location": rj.get("location", "India"),
                        "rawDescription": rj.get("rawDescription", ""),
                        "extractedRequirements": rj.get("extractedRequirements", []),
                        "salaryIntelligence": None,
                        "postedAt": datetime.now(timezone.utc).isoformat(),
                    })
                logger.info(f"[Google] Gemini grounding found {len(results)} jobs as fallback.")
                return results
        except Exception as e:
            logger.warning(f"[Google] Gemini grounding fallback failed: {e}")
        return []

    def _build_salary_intel(
        self, job: Dict[str, Any], snippet: str, criteria: SearchCriteria
    ) -> Dict[str, Any]:
        """Build salary intel for portal discovery results."""
        company = job.get("companyName", "")
        title = job.get("title", "")
        min_exp, max_exp = parse_experience_from_text(f"{title} {snippet}")

        mid_exp = ((min_exp or criteria.min_exp_years) + (max_exp or criteria.max_exp_years)) / 2
        benchmark_lpa = 20.0 + (mid_exp * 2.8)

        return {
            "company_name": company,
            "designation": title,
            "experience_bracket": f"{min_exp or criteria.min_exp_years}-{max_exp or criteria.max_exp_years} Years",
            "estimated_ctc_min_lpa": round(benchmark_lpa * 0.80, 1),
            "estimated_ctc_max_lpa": round(benchmark_lpa * 1.35, 1),
            "estimated_ctc_median_lpa": round(benchmark_lpa * 1.05, 1),
            "fixed_base_percentage": 80.0,
            "variable_pay_details": "10-15% performance bonus standard",
            "esop_details": "Stock options available at funded product companies",
            "ambitionbox_rating": 4.0,
            "glassdoor_rating": 3.9,
            "pros_summary": ["Direct career portal listing — apply directly to avoid ATS filters"],
            "cons_summary": ["Full salary details may not be disclosed upfront"],
            "negotiation_leverage_tips": [
                "Direct portal applications bypass ATS — negotiate directly with hiring manager",
                "Reference Glassdoor / AmbitionBox benchmarks when discussing CTC",
            ],
        }
