"""
Authentication API Routes
=========================
Google OAuth sign-in, email/password login, registration, and resume document ingestion.
"""

import logging
from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, status
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.gcp_clients import db
from app.services.integrations.google_auth import (
    google_auth_service,
    GoogleAuthPayload,
    GoogleAuthResponse,
)
from app.services.matching.resume_parser import resume_parser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


class LoginPayload(BaseModel):
    email: str
    password: Optional[str] = None


class RegisterPayload(BaseModel):
    name: str
    email: str
    password: Optional[str] = None
    targetRole: Optional[str] = "Software Engineer"
    expectedCtcLpa: Optional[float] = 25.0


@router.get("/config", response_model=Dict[str, Any])
async def get_auth_config():
    """
    Returns public client authentication configuration.
    """
    return {
        "googleClientId": settings.GOOGLE_CLIENT_ID or "",
        "environment": "development" if not settings.GOOGLE_CLIENT_ID else "production",
    }


@router.post("/google", response_model=GoogleAuthResponse)
async def login_with_google(payload: GoogleAuthPayload):
    """
    Authenticate candidate using Google OAuth ID token or dev mock login.
    Creates or retrieves the candidate profile and returns session token and user object.
    """
    try:
        response = await google_auth_service.verify_and_authenticate(payload)
        return response
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve),
        )
    except Exception as e:
        logger.error(f"Google Auth failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication failed: {str(e)}",
        )


@router.post("/login", response_model=Dict[str, Any])
async def login_user(payload: LoginPayload):
    """
    Email authentication endpoint. If user exists, retrieves session;
    otherwise auto-provisions candidate profile.
    """
    clean_email = payload.email.strip().lower()
    existing = db.get_user_by_email(clean_email)
    
    if not existing:
        user_id = f"user_{abs(hash(clean_email)) % 1000000}"
        name = clean_email.split("@")[0].capitalize()
        new_profile = {
            "userId": user_id,
            "name": name,
            "fullName": name,
            "email": clean_email,
            "headline": "Senior Software Engineer | Open to Opportunities",
            "currentRole": "Software Engineer",
            "experienceYears": 3.5,
            "yearsExperience": 3.5,
            "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Git", "REST APIs"],
            "additionalSkills": ["Kubernetes", "GCP", "Redis"],
            "currentCtcLpa": 18.0,
            "expectedCtcLpa": 28.0,
            "noticePeriodDays": 30,
            "location": "Bengaluru, Karnataka, India",
            "hasUploadedResume": False,
            "connectedAccounts": {
                "google": {"connected": False},
                "linkedin": {"connected": False},
                "naukri": {"connected": False},
            },
        }
        existing = db.save_user(user_id, new_profile)

    return {
        "token": f"jwt_session_{existing['userId']}",
        "user": existing,
    }


@router.post("/register", response_model=Dict[str, Any])
async def register_user(payload: RegisterPayload):
    """
    Register new candidate persona with custom target role and expected compensation.
    """
    clean_email = payload.email.strip().lower()
    user_id = f"user_{abs(hash(clean_email)) % 1000000}"
    
    profile = {
        "userId": user_id,
        "name": payload.name.strip(),
        "fullName": payload.name.strip(),
        "email": clean_email,
        "headline": f"{payload.targetRole} | Open to Opportunities",
        "currentRole": payload.targetRole,
        "experienceYears": 3.0,
        "yearsExperience": 3.0,
        "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Git"],
        "additionalSkills": ["GCP", "AWS", "Redis"],
        "recommendedPosition": payload.targetRole,
        "recommendedDomain": "Enterprise Software",
        "currentCtcLpa": round((payload.expectedCtcLpa or 25.0) * 0.70, 1),
        "expectedCtcLpa": payload.expectedCtcLpa or 25.0,
        "noticePeriodDays": 30,
        "location": "Bengaluru, Karnataka, India",
        "hasUploadedResume": False,
        "connectedAccounts": {
            "google": {"connected": False},
            "linkedin": {"connected": False},
            "naukri": {"connected": False},
        },
    }
    saved = db.save_user(user_id, profile)
    return {
        "token": f"jwt_session_{user_id}",
        "user": saved,
    }


@router.post("/upload-resume", response_model=Dict[str, Any])
async def upload_resume_document(
    file: UploadFile = File(...),
    userId: Optional[str] = Form(None)
):
    """
    Parses uploaded PDF/DOCX/TXT resume via Gemini Multimodal document ingestion
    or deterministic extraction, creates/updates the candidate persona, and returns session.
    """
    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        parsed = await resume_parser.parse_document_bytes(
            file_bytes=content,
            filename=file.filename or "resume.pdf",
            mime_type=file.content_type or "application/pdf"
        )

        uid = userId or f"user_{abs(hash(parsed.email)) % 1000000}"
        existing = db.get_user(uid) or {"userId": uid}

        # Normalize skills into clean list
        all_skills = list(set(parsed.primary_skills + parsed.secondary_skills + parsed.cloud_and_infrastructure))
        
        user_profile = {
            **existing,
            "userId": uid,
            "name": parsed.full_name or existing.get("name", "Candidate"),
            "fullName": parsed.full_name or existing.get("fullName", "Candidate"),
            "email": parsed.email if parsed.email != "candidate@example.com" else existing.get("email", parsed.email),
            "phone": parsed.phone or existing.get("phone", ""),
            "location": parsed.current_location or existing.get("location", "Bengaluru, India"),
            "currentRole": parsed.current_designation or existing.get("currentRole", "Software Engineer"),
            "headline": f"{parsed.current_designation} | {parsed.years_of_experience} yrs exp",
            "experienceYears": parsed.years_of_experience or existing.get("experienceYears", 3.0),
            "yearsExperience": parsed.years_of_experience or existing.get("yearsExperience", 3.0),
            "skills": all_skills if all_skills else existing.get("skills", ["Python", "FastAPI", "SQL"]),
            "additionalSkills": parsed.cloud_and_infrastructure,
            "recommendedPosition": parsed.recommended_position or parsed.current_designation,
            "recommendedDomain": parsed.recommended_domain or "Enterprise Software",
            "summary": parsed.summary or existing.get("summary", ""),
            "hasUploadedResume": True,
            "resumeFilename": file.filename,
        }

        saved_user = db.save_user(uid, user_profile)

        return {
            "token": f"jwt_session_{uid}",
            "user": saved_user,
            "message": f"Resume '{file.filename}' processed successfully via Gemini Multimodal Ingestion.",
            "parsedData": parsed.model_dump(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Resume upload failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Resume processing failed: {str(e)}"
        )


@router.get("/me/{user_id}", response_model=Dict[str, Any])
async def get_current_user_profile(user_id: str):
    """
    Retrieve candidate profile with connection and sync status.
    """
    user = db.get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate profile not found.",
        )
    return user
