import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from app.core.gcp_clients import db
from app.services.search.query_builder import SearchCriteria
from app.services.search.job_ingestion import job_ingestion_engine
from app.services.research.salary_researcher import research_company_compensation, SalaryIntelligenceReport
from app.services.matching.ats_scorer import ats_scorer

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/jobs", tags=["Jobs & Salary Intelligence"])

class SearchTriggerRequest(BaseModel):
    criteria: SearchCriteria

@router.get("", response_model=List[Dict[str, Any]])
async def list_jobs(
    user_id: Optional[str] = Query(default=None, description="User ID for contextual match scoring"),
    min_match: Optional[float] = Query(default=0.0, description="Filter by minimum match percentage")
):
    """Returns all indexed jobs with live ATS match scoring computed against user profile."""
    jobs = db.get_jobs()
    user = db.get_user(user_id) or {}

    scored_jobs = []
    for job in jobs:
        eval_res = await ats_scorer.evaluate_match(user, job)
        job_copy = dict(job)
        job_copy["matchScore"] = eval_res.matchScore
        job_copy["matchBreakdown"] = eval_res.matchBreakdown.model_dump()
        job_copy["isHighMatch"] = eval_res.isHighMatch
        job_copy["missingSkills"] = eval_res.missingSkills
        job_copy["strengths"] = eval_res.strengths
        job_copy["tailoredAdvice"] = eval_res.tailoredAdvice
        
        if eval_res.matchScore >= min_match:
            scored_jobs.append(job_copy)

    # Sort descending by match score
    scored_jobs.sort(key=lambda x: x.get("matchScore", 0), reverse=True)
    return scored_jobs

@router.get("/{job_id}", response_model=Dict[str, Any])
async def get_job_detail(
    job_id: str,
    user_id: Optional[str] = Query(default=None)
):
    """Fetches full job detail and deep match evaluation."""
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job listing not found.")
    
    user = db.get_user(user_id) or {}
    eval_res = await ats_scorer.evaluate_match(user, job)
    
    job_copy = dict(job)
    job_copy["matchScore"] = eval_res.matchScore
    job_copy["matchBreakdown"] = eval_res.matchBreakdown.model_dump()
    job_copy["isHighMatch"] = eval_res.isHighMatch
    job_copy["missingSkills"] = eval_res.missingSkills
    job_copy["strengths"] = eval_res.strengths
    job_copy["tailoredAdvice"] = eval_res.tailoredAdvice
    return job_copy

@router.post("/ingest", response_model=List[Dict[str, Any]])
async def trigger_ingestion(req: SearchTriggerRequest):
    """Executes live search ingestion across LinkedIn, Naukri, and Google Search Grounding."""
    new_jobs = await job_ingestion_engine.run_ingestion_pipeline(req.criteria)
    return new_jobs

@router.get("/research/salary", response_model=SalaryIntelligenceReport)
async def get_salary_intelligence(
    company: str = Query(..., description="Target company name (e.g. Razorpay, Swiggy, CRED)"),
    role: str = Query(..., description="Target role (e.g. Senior Backend Engineer)"),
    exp_years: int = Query(default=4, description="Years of experience")
):
    """Performs real-time grounded compensation research across AmbitionBox, Glassdoor, and Indian tech benchmarks."""
    report = await research_company_compensation(company=company, role=role, exp_years=exp_years)
    return report
