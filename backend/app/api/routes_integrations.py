"""
Account Integrations API Routes
===============================
LinkedIn and Naukri profile synchronization endpoints.
"""

import logging
from fastapi import APIRouter, HTTPException, status
from typing import Any, Dict

from app.services.integrations.linkedin_connector import (
    linkedin_connector,
    LinkedInSyncRequest,
)
from app.services.integrations.naukri_connector import (
    naukri_connector,
    NaukriSyncRequest,
)
from app.core.gcp_clients import db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/integrations", tags=["Account Integrations"])


@router.post("/linkedin/sync", response_model=Dict[str, Any])
async def sync_linkedin_account(request: LinkedInSyncRequest):
    """
    Sync candidate profile details directly from LinkedIn profile URL or text.
    Extracts skills, headline, experience, and domain expertise.
    """
    try:
        result = await linkedin_connector.sync_profile(request)
        return result
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve),
        )
    except Exception as e:
        logger.error(f"LinkedIn sync failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LinkedIn sync failed: {str(e)}",
        )


@router.post("/naukri/sync", response_model=Dict[str, Any])
async def sync_naukri_account(request: NaukriSyncRequest):
    """
    Sync candidate profile details directly from Naukri profile data.
    Extracts notice period, current/expected CTC, preferred locations, and key skills.
    """
    try:
        result = await naukri_connector.sync_profile(request)
        return result
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve),
        )
    except Exception as e:
        logger.error(f"Naukri sync failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Naukri sync failed: {str(e)}",
        )


@router.get("/status/{user_id}", response_model=Dict[str, Any])
async def get_integration_status(user_id: str):
    """
    Get connection and sync status for all linked accounts (Google, LinkedIn, Naukri).
    """
    user = db.get_user(user_id)
    if not user:
        return {
            "userId": user_id,
            "connectedAccounts": {
                "google": {"connected": False},
                "linkedin": {"connected": False},
                "naukri": {"connected": False},
            },
        }

    connected = user.get("connectedAccounts", {
        "google": {"connected": False},
        "linkedin": {"connected": False},
        "naukri": {"connected": False},
    })

    return {
        "userId": user_id,
        "connectedAccounts": connected,
        "totalSkills": len(user.get("skills", {}).get("primarySkills", [])) + len(user.get("skills", {}).get("secondarySkills", [])),
    }
