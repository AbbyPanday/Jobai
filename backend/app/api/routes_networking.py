"""
Networking Routes — LinkedOut A2A Integration
==============================================
Exposes endpoints for managing the user's LinkedOut agent:
  - Register as a networking agent
  - Post job-seeking intents
  - Browse semantic matches
  - Send pings to hiring manager agents
  - Browse the public LinkedOut feed
"""

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.gcp_clients import db
from app.services.networking.linkedout_client import linkedout_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/networking", tags=["LinkedOut Networking"])


class RegisterAgentRequest(BaseModel):
    userId: str
    handle: str  # Desired agent handle e.g. "abhimanyu_agent"


class PingRequest(BaseModel):
    toAgentId: str
    intentId: str
    rationale: str


# ── Register ───────────────────────────────────────────────────────────────

@router.post("/register", response_model=Dict[str, Any])
async def register_linkedout_agent(req: RegisterAgentRequest):
    """
    Register the user as a LinkedOut agent.
    Uses their stored profile to auto-populate the registration.
    Returns apiKey (save it!) + claimUrl for verification.
    """
    user = db.get_user(req.userId)
    if not user:
        raise HTTPException(status_code=404, detail="User profile not found.")

    raw_skills = user.get("skills", [])
    if isinstance(raw_skills, dict):
        skills = (
            raw_skills.get("primarySkills", [])
            + raw_skills.get("secondarySkills", [])
            + raw_skills.get("domainExpertise", [])
        )
    elif isinstance(raw_skills, list):
        skills = [s for s in raw_skills if isinstance(s, str)]
    else:
        skills = []

    tags = [s.lower().replace(" ", "-") for s in skills[:8]]
    tags += ["india", "backend", "tech"]

    result = await linkedout_client.register_agent(
        display_name=user.get("name") or user.get("fullName", "Candidate"),
        headline=f"{user.get('currentRole', 'Software Engineer')} | {user.get('experienceYears', 3)}+ yrs | {', '.join(skills[:3])}",
        bio=user.get("summary", f"Experienced {user.get('currentRole', 'engineer')} with {user.get('experienceYears', 3)} years in {', '.join(skills[:4])}."),
        tags=list(set(tags))[:10],
        location=user.get("location", "India"),
        handle=req.handle,
    )

    if not result.get("apiKey"):
        raise HTTPException(
            status_code=500,
            detail="LinkedOut registration failed. Check LINKEDOUT_API_KEY or try a different handle."
        )

    # Store agent handle in user profile
    db.save_user(req.userId, {"linkedOutHandle": req.handle, "linkedOutRegistered": True})

    return {
        "success": True,
        "apiKey": result.get("apiKey"),
        "claimUrl": result.get("claimUrl"),
        "verificationCode": result.get("verificationCode"),
        "agentId": result.get("agentId"),
        "humanId": result.get("humanId"),
        "handle": req.handle,
        "message": (
            "✅ LinkedOut agent registered! "
            "Share the claimUrl with your user to verify their profile via Twitter/X post. "
            "IMPORTANT: Save the apiKey — it won't be shown again."
        ),
    }


# ── Intent Posting ─────────────────────────────────────────────────────────

@router.post("/post-intent", response_model=Dict[str, Any])
async def post_job_seeking_intent(userId: str = Query(...)):
    """
    Post a job-seeking 'ask' intent on LinkedOut using the user's profile.
    This gets semantically matched against hiring manager offer intents.
    """
    user = db.get_user(userId)
    if not user:
        raise HTTPException(status_code=404, detail="User profile not found.")

    intent = await linkedout_client.create_job_seeking_intent(user)
    if not intent:
        raise HTTPException(
            status_code=503,
            detail="Could not post intent. Ensure LinkedOut agent is registered and API key is set."
        )

    return {"success": True, "intent": intent}


# ── Matches ────────────────────────────────────────────────────────────────

@router.get("/matches", response_model=List[Dict[str, Any]])
async def get_network_matches(
    limit: int = Query(default=10, le=20),
    category: str = Query(default="jobs"),
):
    """
    Fetch semantically matched agents (hiring managers, founders, investors)
    whose intents complement the user's job-seeking ask.
    """
    matches = await linkedout_client.get_matches(limit=limit, category=category)
    return matches


# ── Pings ─────────────────────────────────────────────────────────────────

@router.post("/ping", response_model=Dict[str, Any])
async def send_connection_ping(req: PingRequest):
    """
    Send a connection ping to a matched hiring agent.
    Both agents must accept before humans are connected.
    Pings expire after 7 days.
    """
    result = await linkedout_client.send_ping(
        to_agent_id=req.toAgentId,
        intent_id=req.intentId,
        rationale=req.rationale,
    )
    if not result:
        raise HTTPException(status_code=503, detail="Failed to send ping.")
    return {"success": True, "ping": result}


@router.get("/pings", response_model=List[Dict[str, Any]])
async def list_pings(direction: str = Query(default="all")):
    """List sent and/or received pings."""
    return await linkedout_client.list_pings(direction=direction)


# ── Feed ──────────────────────────────────────────────────────────────────

@router.get("/feed", response_model=List[Dict[str, Any]])
async def browse_feed(
    limit: int = Query(default=20, le=50),
    category: Optional[str] = Query(default=None),
):
    """Browse recent intents from all LinkedOut agents (no auth required)."""
    return await linkedout_client.get_feed(limit=limit, category=category)


# ── Status ────────────────────────────────────────────────────────────────

@router.get("/status", response_model=Dict[str, Any])
async def networking_status():
    """Check LinkedOut integration status."""
    return {
        "configured": linkedout_client.is_configured,
        "authenticated": linkedout_client._jwt_token is not None,
        "agentId": linkedout_client._agent_id,
        "message": (
            "LinkedOut integration active."
            if linkedout_client.is_configured
            else "Add LINKEDOUT_API_KEY to .env to enable A2A networking."
        ),
    }
