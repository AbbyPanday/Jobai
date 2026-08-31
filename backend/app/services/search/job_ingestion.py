"""
Job Ingestion Engine (Orchestrator)
=====================================
Runs parallel ingestion across LinkedIn, Naukri, and Google Discovery,
deduplicates by URL, runs immediate ATS scoring, and stores results.

Deduplication strategy:
  1. Primary: Normalized URL (strips query params, lowercased)
  2. Secondary: company::title fuzzy match (catches same job on multiple boards)
"""

import asyncio
import hashlib
import logging
from typing import Any, Dict, List, Optional, Set

from app.core.gcp_clients import db
from app.services.matching.ats_scorer import ats_scorer
from app.services.search.query_builder import SearchCriteria
from app.services.search.linkedin_worker import LinkedInSearchWorker
from app.services.search.naukri_worker import NaukriSearchWorker
from app.services.search.google_search_worker import GoogleSearchWorker

logger = logging.getLogger(__name__)


def _url_key(url: str) -> str:
    """Stable dedup key from URL."""
    from app.services.search.serper_client import _normalize_url
    return _normalize_url(url)


def _title_company_key(job: Dict[str, Any]) -> str:
    """
    Secondary dedup key: normalized (company + title) hash.
    Catches same job posted on both LinkedIn and Naukri.
    """
    c = job.get("companyName", "").lower().strip()
    t = job.get("title", "").lower().strip()
    # Remove common noise words from title
    for noise in ["senior", "lead", "principal", "staff", "-", "|", "–"]:
        t = t.replace(noise, "").strip()
    return hashlib.md5(f"{c}::{t[:40]}".encode()).hexdigest()[:16]


class JobIngestionEngine:
    """
    Orchestrates multi-source job discovery and ATS scoring.
    """

    def __init__(self):
        self.linkedin_worker = LinkedInSearchWorker()
        self.naukri_worker = NaukriSearchWorker()
        self.google_worker = GoogleSearchWorker()

    async def run_ingestion_pipeline(
        self,
        criteria: SearchCriteria,
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Full pipeline:
          1. Parallel ingestion from all 3 sources
          2. URL + title deduplication
          3. Immediate ATS scoring per job (if user profile available)
          4. Persist to database
          5. Return scored, sorted results

        Args:
            criteria:   Search criteria (titles, skills, locations, exp)
            user_id:    Optional user ID to score against their profile
        """
        logger.info("=" * 60)
        logger.info("Job Ingestion Pipeline: START")
        logger.info(f"  Titles:    {criteria.titles}")
        logger.info(f"  Skills:    {criteria.required_skills}")
        logger.info(f"  Locations: {criteria.locations}")
        logger.info(f"  Exp:       {criteria.min_exp_years}-{criteria.max_exp_years} yrs")
        logger.info("=" * 60)

        # Step 1: Parallel fetch from all sources
        results = await asyncio.gather(
            self.linkedin_worker.search_jobs(criteria),
            self.naukri_worker.search_jobs(criteria),
            self.google_worker.search_jobs(criteria),
            return_exceptions=True,
        )

        source_labels = ["LinkedIn", "Naukri", "Google"]
        all_jobs: List[Dict[str, Any]] = []
        for label, res in zip(source_labels, results):
            if isinstance(res, list):
                logger.info(f"  {label}: {len(res)} raw results")
                all_jobs.extend(res)
            elif isinstance(res, Exception):
                logger.error(f"  {label} worker failed: {res}")

        logger.info(f"Total raw: {len(all_jobs)} listings across all sources")

        # Step 2: Deduplication
        unique_jobs = self._deduplicate(all_jobs)
        logger.info(f"After dedup: {len(unique_jobs)} unique listings")

        # Step 3: ATS scoring (run concurrently, max 5 at a time)
        user_profile = db.get_user(user_id) if user_id else {}
        sem = asyncio.Semaphore(5)
        scored_jobs = await asyncio.gather(
            *[self._score_and_save(job, user_profile or {}, sem) for job in unique_jobs],
            return_exceptions=True,
        )

        final_jobs: List[Dict[str, Any]] = []
        for result in scored_jobs:
            if isinstance(result, dict):
                final_jobs.append(result)
            elif isinstance(result, Exception):
                logger.debug(f"Scoring error: {result}")

        # Step 4: Sort by match score descending
        final_jobs.sort(key=lambda x: (x.get("matchScore") if x.get("matchScore") is not None else 0.0), reverse=True)

        logger.info(f"Pipeline COMPLETE: {len(final_jobs)} jobs ingested and scored.")
        logger.info("=" * 60)
        return final_jobs

    def _deduplicate(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Two-pass deduplication:
        Pass 1: exact URL match
        Pass 2: company + title fuzzy match (to remove cross-board duplicates)
        """
        seen_urls: Set[str] = set()
        seen_title_company: Set[str] = set()
        unique: List[Dict[str, Any]] = []

        for job in jobs:
            url = job.get("_normalizedUrl") or _url_key(job.get("externalUrl", ""))
            tc_key = _title_company_key(job)

            if url and url in seen_urls:
                continue
            if tc_key in seen_title_company:
                continue

            if url:
                seen_urls.add(url)
            seen_title_company.add(tc_key)
            unique.append(job)

        return unique

    async def _score_and_save(
        self,
        job: Dict[str, Any],
        user_profile: Dict[str, Any],
        sem: asyncio.Semaphore,
    ) -> Dict[str, Any]:
        """Score a job against user profile, enrich the job dict, and save to DB."""
        async with sem:
            try:
                if user_profile:
                    evaluation = await ats_scorer.evaluate_match(user_profile, job)
                    job["matchScore"] = evaluation.matchScore
                    job["matchBreakdown"] = evaluation.matchBreakdown.model_dump()
                    job["isHighMatch"] = evaluation.isHighMatch
                    job["missingSkills"] = evaluation.missingSkills
                    job["strengths"] = evaluation.strengths
                    job["tailoredAdvice"] = evaluation.tailoredAdvice
                else:
                    # No user profile — leave scores as None, frontend will show "--"
                    job.setdefault("matchScore", None)
                    job.setdefault("isHighMatch", False)

                job_id = job.get("jobId")
                if job_id:
                    db.save_job(job_id, job)

            except Exception as e:
                logger.warning(f"Scoring/save error for {job.get('jobId')}: {e}")

            return job


# Global singleton
job_ingestion_engine = JobIngestionEngine()
