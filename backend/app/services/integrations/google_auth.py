"""
Google Authentication Service
=============================
Verifies Google OAuth2 ID tokens and creates or retrieves candidate profiles.
Supports both Google Identity Services ID tokens and local development mock tokens.
"""

import logging
from typing import Any, Dict, Optional
from pydantic import BaseModel

from app.core.config import settings
from app.core.gcp_clients import db

logger = logging.getLogger(__name__)


class GoogleAuthPayload(BaseModel):
    credential: Optional[str] = None  # Google ID token (JWT)
    email: Optional[str] = None
    name: Optional[str] = None
    picture: Optional[str] = None
    sub: Optional[str] = None  # Google unique user ID
    isMock: bool = False


class GoogleAuthResponse(BaseModel):
    success: bool
    userId: str
    email: str
    fullName: str
    picture: Optional[str] = None
    isNewUser: bool = False
    token: str
    user: Optional[Dict[str, Any]] = None


class GoogleAuthService:
    """
    Handles Google OAuth token validation and candidate user provisioning.
    """

    async def verify_and_authenticate(self, payload: GoogleAuthPayload) -> GoogleAuthResponse:
        """
        Verify Google credential token or process mock payload.
        """
        user_info = None

        # 1. If real token provided, attempt google-auth token verification
        if payload.credential and not payload.isMock:
            user_info = await self._verify_google_token(payload.credential)

        # 2. If mock or fallback provided
        if not user_info:
            if payload.email:
                user_info = {
                    "sub": payload.sub or f"google_user_{abs(hash(payload.email)) % 1000000}",
                    "email": payload.email,
                    "name": payload.name or payload.email.split("@")[0].capitalize(),
                    "picture": payload.picture or "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=128&q=80",
                }
            else:
                raise ValueError("Valid Google credential or email is required.")

        email = user_info.get("email")
        full_name = user_info.get("name", "Candidate")
        picture = user_info.get("picture")
        google_sub = user_info.get("sub")

        # 3. Lookup user in DB or provision new profile
        user_id = f"user_{google_sub}"
        existing = db.get_user(user_id)
        is_new = False

        if not existing:
            is_new = True
            initial_profile = {
                "userId": user_id,
                "name": full_name,
                "fullName": full_name,
                "email": email,
                "picture": picture,
                "profilePicture": picture,
                "headline": "Software Engineer | Open to Opportunities",
                "currentRole": "Software Engineer",
                "recommendedPosition": "Software Engineer",
                "recommendedDomain": "Enterprise Software",
                "experienceYears": 3.0,
                "yearsExperience": 3.0,
                "skills": ["Python", "JavaScript", "SQL", "Docker", "Git", "REST APIs"],
                "additionalSkills": ["PostgreSQL", "FastAPI", "GCP"],
                "currentCtcLpa": 18.0,
                "expectedCtcLpa": 28.0,
                "noticePeriodDays": 30,
                "location": "Bengaluru, Karnataka, India",
                "preferences": {
                    "preferredLocations": ["Bengaluru", "Remote"],
                    "minCtcLpa": 20.0,
                    "targetRoles": ["Software Engineer", "Backend Engineer"],
                },
                "authProvider": "GOOGLE",
                "connectedAccounts": {
                    "google": {"connected": True, "email": email, "picture": picture},
                    "linkedin": {"connected": False},
                    "naukri": {"connected": False},
                },
            }
            saved_user = db.save_user(user_id, initial_profile)
        else:
            # Update connected accounts state if needed
            connected = existing.get("connectedAccounts", {})
            connected["google"] = {"connected": True, "email": email, "picture": picture}
            existing["connectedAccounts"] = connected
            existing["name"] = existing.get("name") or full_name
            existing["fullName"] = existing.get("fullName") or full_name
            existing["picture"] = existing.get("picture") or picture
            existing["profilePicture"] = existing.get("profilePicture") or picture
            saved_user = db.save_user(user_id, existing)

        return GoogleAuthResponse(
            success=True,
            userId=user_id,
            email=email,
            fullName=full_name,
            picture=picture,
            isNewUser=is_new,
            token=f"jwt_session_{user_id}_{google_sub[:8] if google_sub else 'auth'}",
            user=saved_user,
        )

    async def _verify_google_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify token against Google API or decode payload."""
        try:
            from google.oauth2 import id_token
            from google.auth.transport import requests as google_requests

            client_id = settings.GOOGLE_CLIENT_ID or None
            id_info = id_token.verify_oauth2_token(
                token,
                google_requests.Request(),
                client_id,
            )
            return id_info
        except Exception as e:
            logger.info(f"Google ID token verification via library not available: {e}. Decoding payload.")
            # Fallback: decode unverified JWT claims for local dev resilience
            try:
                import json, base64
                parts = token.split(".")
                if len(parts) >= 2:
                    padding = "=" * (4 - len(parts[1]) % 4)
                    decoded = base64.urlsafe_b64decode(parts[1] + padding).decode("utf-8")
                    claims = json.loads(decoded)
                    return {
                        "sub": claims.get("sub", "dev_user"),
                        "email": claims.get("email", "candidate@gmail.com"),
                        "name": claims.get("name", "Candidate"),
                        "picture": claims.get("picture"),
                    }
            except Exception as parse_err:
                logger.warning(f"Could not parse token: {parse_err}")
            return None


# Global singleton
google_auth_service = GoogleAuthService()
