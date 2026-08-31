"""
LinkedOut API Client
====================
Async REST client wrapping the LinkedOut A2A networking platform (linkedout.so).

Enables your job agent to:
  1. Register as a networking agent for the user
  2. Post job-seeking "asks" as intents
  3. Discover matched hiring manager agents
  4. Send / receive connection pings

LinkedOut gives access to off-market roles posted directly by
founders, hiring managers, and investors — bypassing ATS entirely.

Ref: https://www.linkedout.so/skill.md
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class LinkedOutClient:
    """
    Async LinkedOut REST API client with JWT token management.
    JWT tokens expire after 60 min — auto-refreshed transparently.
    """

    BASE_URL = settings.LINKEDOUT_BASE_URL

    def __init__(self):
        self._api_key: Optional[str] = settings.LINKEDOUT_API_KEY or None
        self._jwt_token: Optional[str] = None
        self._token_expires_at: float = 0.0
        self._agent_id: Optional[str] = None
        self._human_id: Optional[str] = None

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    # ── Authentication ──────────────────────────────────────────────────────

    async def register_agent(
        self,
        display_name: str,
        headline: str,
        bio: str,
        tags: List[str],
        location: str,
        handle: str,
    ) -> Dict[str, Any]:
        """
        Register a new human profile + agent on LinkedOut.
        Returns apiKey (save it!), claimUrl, verificationCode, agentId, humanId.
        
        NOTE: apiKey is shown ONCE. Store it immediately.
        """
        payload = {
            "human": {
                "type": "person",
                "displayName": display_name,
                "headline": headline,
                "bio": bio,
                "tags": tags,
                "location": location,
            },
            "agent": {
                "handle": handle,
                "capabilities": ["networking", "intents", "pings"],
            },
        }
        result = await self._post("/api/agents/register", payload, auth=False)
        if result and result.get("apiKey"):
            self._api_key = result["apiKey"]
            self._agent_id = result.get("agentId")
            self._human_id = result.get("humanId")
            logger.info(f"LinkedOut agent registered: @{handle} (agentId={self._agent_id})")
        return result or {}

    async def get_jwt_token(self) -> Optional[str]:
        """Exchange API key for JWT. Token valid for 60 minutes."""
        if not self._api_key:
            return None
        result = await self._post(
            "/api/agents/token", {"apiKey": self._api_key}, auth=False
        )
        if result and result.get("token"):
            self._jwt_token = result["token"]
            self._token_expires_at = time.time() + (result.get("expiresIn", 3600) - 60)
            self._agent_id = result.get("agentId") or self._agent_id
            logger.debug("LinkedOut JWT token refreshed.")
            return self._jwt_token
        return None

    async def _ensure_token(self) -> bool:
        """Ensure a valid JWT token exists, refreshing if expired."""
        if not self._api_key:
            return False
        if not self._jwt_token or time.time() >= self._token_expires_at:
            token = await self.get_jwt_token()
            return token is not None
        return True

    # ── Intents ─────────────────────────────────────────────────────────────

    async def create_job_seeking_intent(
        self,
        user_profile: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Post a 'jobs' ask intent on LinkedOut representing the user's job search.
        This gets semantically matched against hiring manager "offer" intents.
        """
        if not await self._ensure_token():
            logger.warning("LinkedOut: Cannot create intent — not authenticated.")
            return None

        role = user_profile.get("currentRole", "Software Engineer")
        raw_skills = user_profile.get("skills", [])
        if isinstance(raw_skills, dict):
            skills_list = (
                raw_skills.get("primarySkills", [])
                + raw_skills.get("secondarySkills", [])
                + raw_skills.get("domainExpertise", [])
            )
        elif isinstance(raw_skills, list):
            skills_list = [s for s in raw_skills if isinstance(s, str)]
        else:
            skills_list = []

        skills = skills_list[:6]
        exp = user_profile.get("experienceYears", 3)
        location = user_profile.get("location", "India")
        exp_ctc = user_profile.get("expectedCtcLpa", 0)

        text = (
            f"Experienced {role} with {exp} years, skilled in {', '.join(skills)}. "
            f"Looking for senior/lead engineering roles in India (open to remote). "
            + (f"Expected CTC: ₹{exp_ctc} LPA. " if exp_ctc else "")
            + "Strong background in cloud-native distributed systems."
        )

        tags = [s.lower().replace(" ", "-") for s in skills[:5]]
        tags += ["india", "backend", "cloud"]

        payload = {
            "type": "ask",
            "category": "jobs",
            "text": text,
            "tags": list(set(tags))[:10],
            "constraints": {
                "geo": [location.split(",")[0], "Remote"],
                "industry": ["SaaS", "FinTech", "Developer Tools", "E-Commerce"],
                "stage": ["senior", "lead", "staff"],
            },
        }
        result = await self._post("/api/intents", payload)
        if result and result.get("id"):
            logger.info(f"LinkedOut intent created: {result['id']}")
        return result

    async def get_matches(
        self,
        limit: int = 10,
        category: str = "jobs",
    ) -> List[Dict[str, Any]]:
        """
        Fetch semantically matched intents from other agents.
        Returns hiring manager agents whose "offer" intents match your "ask".
        """
        if not await self._ensure_token():
            return []

        params = f"?limit={limit}&category={category}"
        result = await self._get(f"/api/matches{params}")
        return (result or {}).get("matches", [])

    async def send_ping(
        self,
        to_agent_id: str,
        intent_id: str,
        rationale: str,
    ) -> Optional[Dict[str, Any]]:
        """Request a connection with a matched hiring agent."""
        if not await self._ensure_token():
            return None

        payload = {
            "toAgentId": to_agent_id,
            "intentId": intent_id,
            "rationale": rationale,
        }
        return await self._post("/api/pings", payload)

    async def list_pings(self, direction: str = "all") -> List[Dict[str, Any]]:
        """List sent/received pings."""
        if not await self._ensure_token():
            return []
        result = await self._get(f"/api/pings?direction={direction}")
        return result if isinstance(result, list) else []

    async def get_feed(self, limit: int = 20, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Browse recent intents from all agents (no auth required)."""
        params = f"?limit={limit}" + (f"&category={category}" if category else "")
        result = await self._get(f"/api/feed{params}", auth=False)
        return result if isinstance(result, list) else []

    # ── HTTP Helpers ────────────────────────────────────────────────────────

    async def _post(
        self,
        path: str,
        payload: Dict[str, Any],
        auth: bool = True,
    ) -> Optional[Dict[str, Any]]:
        headers = {"Content-Type": "application/json"}
        if auth and self._jwt_token:
            headers["Authorization"] = f"Bearer {self._jwt_token}"
        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                resp = await client.post(
                    f"{self.BASE_URL}{path}", json=payload, headers=headers
                )
            if resp.status_code in (200, 201):
                return resp.json()
            logger.warning(f"LinkedOut POST {path} → {resp.status_code}: {resp.text[:200]}")
            return None
        except Exception as e:
            logger.error(f"LinkedOut POST {path} error: {e}")
            return None

    async def _get(
        self,
        path: str,
        auth: bool = True,
    ) -> Optional[Any]:
        headers = {}
        if auth and self._jwt_token:
            headers["Authorization"] = f"Bearer {self._jwt_token}"
        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                resp = await client.get(f"{self.BASE_URL}{path}", headers=headers)
            if resp.status_code == 200:
                return resp.json()
            logger.warning(f"LinkedOut GET {path} → {resp.status_code}: {resp.text[:200]}")
            return None
        except Exception as e:
            logger.error(f"LinkedOut GET {path} error: {e}")
            return None


# Global singleton
linkedout_client = LinkedOutClient()
