import os
import json
import logging
from typing import Dict, Any, Optional, List
from app.core.config import settings

logger = logging.getLogger(__name__)

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    genai = None
    types = None
    GENAI_AVAILABLE = False

def get_genai_client() -> Optional[Any]:
    """Returns an initialized Google Gen AI Client if API key is provided, or None."""
    if not GENAI_AVAILABLE:
        return None
    api_key = settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return None
    try:
        return genai.Client(api_key=api_key)
    except Exception as e:
        logger.warning(f"Could not initialize GenAI client: {e}.")
        return None


class LocalStore:
    """
    Firestore-compatible data persistence store for users, indexed jobs, and applications.
    """
    def __init__(self):
        self._users: Dict[str, Dict[str, Any]] = {}
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._applications: Dict[str, Dict[str, Any]] = {}

    def _normalize_user(self, user: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not user:
            return None
        u = dict(user)
        # Sync name & fullName
        if "name" in u and "fullName" not in u:
            u["fullName"] = u["name"]
        elif "fullName" in u and "name" not in u:
            u["name"] = u["fullName"]

        # Sync experienceYears & yearsExperience
        if "experienceYears" in u and "yearsExperience" not in u:
            u["yearsExperience"] = u["experienceYears"]
        elif "yearsExperience" in u and "experienceYears" not in u:
            u["experienceYears"] = u["yearsExperience"]

        # Sync picture & profilePicture
        if "picture" in u and "profilePicture" not in u:
            u["profilePicture"] = u["picture"]
        elif "profilePicture" in u and "picture" not in u:
            u["picture"] = u["profilePicture"]

        # Ensure connected accounts dict
        if "connectedAccounts" not in u:
            u["connectedAccounts"] = {
                "google": {"connected": bool(u.get("authProvider") == "GOOGLE")},
                "linkedin": {"connected": False},
                "naukri": {"connected": False},
            }
        return u

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        return self._normalize_user(self._users.get(user_id))

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        clean = email.strip().lower()
        for user in self._users.values():
            if user.get("email", "").strip().lower() == clean:
                return self._normalize_user(user)
        return None

    def save_user(self, user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        merged = {**self._users.get(user_id, {}), **data}
        normalized = self._normalize_user(merged) or merged
        self._users[user_id] = normalized
        return normalized

    def get_jobs(self) -> List[Dict[str, Any]]:
        return list(self._jobs.values())

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self._jobs.get(job_id)

    def save_job(self, job_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        self._jobs[job_id] = {**self._jobs.get(job_id, {}), **data}
        return self._jobs[job_id]

    def get_applications(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        apps = list(self._applications.values())
        if user_id:
            return [a for a in apps if a.get("userId") == user_id]
        return apps

    def get_application(self, app_id: str) -> Optional[Dict[str, Any]]:
        return self._applications.get(app_id)

    def save_application(self, app_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        existing = self._applications.get(app_id, {})
        merged = {**existing, **data}
        self._applications[app_id] = merged
        return merged

# Global database instance
db = LocalStore()
