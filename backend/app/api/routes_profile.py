import logging
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field
from app.core.gcp_clients import db
from app.services.matching.resume_parser import resume_parser

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/profile", tags=["User Profile & Master Persona"])

class UserProfileUpdate(BaseModel):
    name: Optional[str] = None
    fullName: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    currentRole: Optional[str] = None
    headline: Optional[str] = None
    experienceYears: Optional[float] = None
    yearsExperience: Optional[float] = None
    currentCtcLpa: Optional[float] = None
    expectedCtcLpa: Optional[float] = None
    noticePeriodDays: Optional[int] = None
    skills: Optional[Any] = None
    additionalSkills: Optional[List[str]] = None
    autoApplyThreshold: Optional[float] = None
    summary: Optional[str] = None


class ResumeUploadText(BaseModel):
    resumeText: str


def _extract_flat_skills(skills_field: Any) -> List[str]:
    """Helper to convert skills field into a flat list of strings safely."""
    if isinstance(skills_field, list):
        return [s for s in skills_field if isinstance(s, str)]
    elif isinstance(skills_field, dict):
        res = []
        for k, v in skills_field.items():
            if isinstance(v, list):
                res.extend([x for x in v if isinstance(x, str)])
        return res
    return []


@router.get("/{user_id}", response_model=Dict[str, Any])
async def get_profile(user_id: str):
    """Fetches candidate profile and master persona."""
    user = db.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Candidate profile not found.")
    return user


@router.put("/{user_id}", response_model=Dict[str, Any])
async def update_profile(user_id: str, updates: UserProfileUpdate):
    """Updates candidate persona attributes and preferences."""
    cleaned = {k: v for k, v in updates.model_dump().items() if v is not None}
    
    # Sync name and fullName
    if "name" in cleaned and "fullName" not in cleaned:
        cleaned["fullName"] = cleaned["name"]
    elif "fullName" in cleaned and "name" not in cleaned:
        cleaned["name"] = cleaned["fullName"]

    # Sync experienceYears and yearsExperience
    if "experienceYears" in cleaned and "yearsExperience" not in cleaned:
        cleaned["yearsExperience"] = cleaned["experienceYears"]
    elif "yearsExperience" in cleaned and "experienceYears" not in cleaned:
        cleaned["experienceYears"] = cleaned["yearsExperience"]

    updated = db.save_user(user_id, cleaned)
    return updated


@router.post("/{user_id}/resume", response_model=Dict[str, Any])
async def upload_resume_text(user_id: str, req: ResumeUploadText):
    """Parses resume text using Gemini AI and syncs candidate profile."""
    parsed = await resume_parser.parse_resume_text(req.resumeText)
    
    # Merge with profile
    user = db.get_user(user_id) or {"userId": user_id}
    name = parsed.full_name or user.get("name", "Candidate")
    user["name"] = name
    user["fullName"] = name
    user["email"] = parsed.email or user.get("email")
    user["phone"] = parsed.phone or user.get("phone")
    user["location"] = parsed.current_location or user.get("location")
    user["currentRole"] = parsed.current_designation or user.get("currentRole")
    user["headline"] = f"{parsed.current_designation} | {parsed.years_of_experience} yrs exp"
    user["experienceYears"] = parsed.years_of_experience or user.get("experienceYears", 3.0)
    user["yearsExperience"] = parsed.years_of_experience or user.get("yearsExperience", 3.0)
    user["summary"] = parsed.summary or user.get("summary", "")
    user["hasUploadedResume"] = True

    # Safely merge skills
    existing_skills = _extract_flat_skills(user.get("skills", []))
    existing_addl = _extract_flat_skills(user.get("additionalSkills", []))

    user["skills"] = list(set(existing_skills + parsed.primary_skills))
    user["additionalSkills"] = list(set(existing_addl + parsed.secondary_skills + parsed.cloud_and_infrastructure))
    
    saved = db.save_user(user_id, user)
    return {
        "message": "Resume parsed and profile enriched successfully.",
        "parsedData": parsed.model_dump(),
        "user": saved
    }


@router.post("/{user_id}/resume-upload", response_model=Dict[str, Any])
async def upload_resume_file(user_id: str, file: UploadFile = File(...)):
    """Multipart file upload for PDF/DOCX/TXT resumes directly to user profile."""
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    parsed = await resume_parser.parse_document_bytes(
        file_bytes=content,
        filename=file.filename or "resume.pdf",
        mime_type=file.content_type or "application/pdf"
    )

    user = db.get_user(user_id) or {"userId": user_id}
    name = parsed.full_name or user.get("name", "Candidate")
    user["name"] = name
    user["fullName"] = name
    user["email"] = parsed.email or user.get("email")
    user["phone"] = parsed.phone or user.get("phone")
    user["location"] = parsed.current_location or user.get("location")
    user["currentRole"] = parsed.current_designation or user.get("currentRole")
    user["headline"] = f"{parsed.current_designation} | {parsed.years_of_experience} yrs exp"
    user["experienceYears"] = parsed.years_of_experience or user.get("experienceYears", 3.0)
    user["yearsExperience"] = parsed.years_of_experience or user.get("yearsExperience", 3.0)
    user["summary"] = parsed.summary or user.get("summary", "")
    user["hasUploadedResume"] = True
    user["resumeFilename"] = file.filename

    existing_skills = _extract_flat_skills(user.get("skills", []))
    existing_addl = _extract_flat_skills(user.get("additionalSkills", []))

    user["skills"] = list(set(existing_skills + parsed.primary_skills))
    user["additionalSkills"] = list(set(existing_addl + parsed.secondary_skills + parsed.cloud_and_infrastructure))

    saved = db.save_user(user_id, user)
    return {
        "message": f"Resume '{file.filename}' processed successfully.",
        "parsedData": parsed.model_dump(),
        "user": saved
    }
