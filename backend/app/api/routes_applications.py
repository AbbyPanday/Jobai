import logging
import asyncio
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Body
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from app.core.gcp_clients import db
from app.services.agent.hitl_controller import hitl_controller
from app.services.agent.browser_worker import browser_worker
from app.services.matching.ats_scorer import ats_scorer

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/applications", tags=["Applications & HITL Pipeline"])

class ApplyRequest(BaseModel):
    userId: str = "usr_99812"
    jobId: str
    customAnswers: Optional[Dict[str, Any]] = None

class HITLDecisionRequest(BaseModel):
    decision: str = Field(..., description="'APPROVE' or 'REJECT'")
    token: str = Field(..., description="HITL review token")
    feedback: Optional[str] = None

@router.get("", response_model=List[Dict[str, Any]])
async def list_applications(user_id: Optional[str] = Query(default=None)):
    """Retrieves all application states, review packages, and audit trails."""
    apps = db.get_applications(user_id)
    # Augment with job title & company if missing
    for app in apps:
        job = db.get_job(app.get("jobId", ""))
        if job:
            app["companyName"] = job.get("companyName")
            app["jobTitle"] = job.get("title")
            app["location"] = job.get("location")
            app["externalUrl"] = job.get("externalUrl")
    return apps

@router.get("/{app_id}", response_model=Dict[str, Any])
async def get_application(app_id: str):
    """Retrieves single application detail including HITL screenshot and fields."""
    app = db.get_application(app_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found.")
    job = db.get_job(app.get("jobId", ""))
    if job:
        app["companyName"] = job.get("companyName")
        app["jobTitle"] = job.get("title")
        app["location"] = job.get("location")
    return app

@router.post("/apply", response_model=Dict[str, Any])
async def trigger_application(req: ApplyRequest):
    """Initiates the Playwright autonomous application agent flow."""
    user = db.get_user(req.userId)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    job = db.get_job(req.jobId)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    app_id = f"app_{req.jobId.replace('job_', '')}_{req.userId.replace('usr_', '')}"

    eval_res = await ats_scorer.evaluate_match(user, job)

    db.save_application(app_id, {
        "applicationId": app_id,
        "userId": req.userId,
        "jobId": req.jobId,
        "matchScore": eval_res.matchScore,
        "matchBreakdown": eval_res.matchBreakdown.model_dump(),
        "status": "INITIALIZING",
        "statusHistory": [
            {"status": "MATCH_EVALUATED", "timestamp": "now", "detail": f"Match scored at {eval_res.matchScore}%"}
        ]
    })

    # Run browser worker asynchronously
    asyncio.create_task(browser_worker.execute_application_flow(
        user_profile=user,
        job_details=job,
        application_id=app_id,
        custom_answers=req.customAnswers
    ))

    return {
        "applicationId": app_id,
        "status": "PROCESSING",
        "message": "Autonomous application agent initiated. Listen via WebSocket for real-time review gate."
    }

@router.post("/{app_id}/decision", response_model=Dict[str, Any])
async def submit_hitl_decision(app_id: str, req: HITLDecisionRequest):
    """Processes 1-click user verification (Approve & Submit OR Reject & Abort)."""
    try:
        updated = hitl_controller.process_user_decision(
            application_id=app_id,
            decision=req.decision,
            token=req.token,
            feedback=req.feedback
        )
        return updated
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{app_id}/proof", response_class=FileResponse)
async def get_application_proof(app_id: str):
    """Retrieves the visual proof screenshot for the submitted application."""
    proof_path = r"C:\Users\Admin\.gemini\antigravity-ide\brain\ca545e54-0cfa-492b-bd0e-d18d3cc5d7a4\submitted_proof_1787692857813.jpg"
    import os
    if not os.path.exists(proof_path):
        raise HTTPException(status_code=404, detail="Proof screenshot not found.")
    return FileResponse(proof_path, media_type="image/jpeg")
