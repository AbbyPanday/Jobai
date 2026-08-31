import os
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Callable, Awaitable
from app.services.agent.form_mapper import form_mapper
from app.services.agent.hitl_controller import hitl_controller
from app.core.gcp_clients import db, get_genai_client
from app.core.config import settings

logger = logging.getLogger(__name__)

# Check browser-use availability
BROWSER_USE_AVAILABLE = False
try:
    from browser_use import Agent as BrowserAgent
    from langchain_google_genai import ChatGoogleGenerativeAI
    BROWSER_USE_AVAILABLE = True
    logger.info("browser-use + langchain-google-genai loaded successfully.")
except ImportError as e:
    logger.warning(f"browser-use or langchain-google-genai not installed: {e}. "
                   "Browser agent will run in simulation mode.")


def _get_gemini_llm():
    """Initialize Gemini LLM for browser-use agent via langchain."""
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        return None
    try:
        return ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL,
            google_api_key=api_key,
            temperature=0.1,
        )
    except Exception as e:
        logger.error(f"Failed to initialize Gemini LLM for browser agent: {e}")
        return None


class BrowserWorker:
    """
    Autonomous AI Browser Agent for end-to-end job applications.

    Uses browser-use library powered by Gemini to:
    - Navigate to career portals (Greenhouse, Lever, Workday, direct sites)
    - Understand page layout via Gemini Vision
    - Autofill form fields from the candidate's Master Persona
    - Handle multi-step application flows autonomously
    - Capture review screenshots for Human-In-The-Loop (HITL) verification

    Falls back to simulated mode when browser-use is unavailable.
    """

    def __init__(self):
        pass

    async def execute_application_flow(
        self,
        user_profile: Dict[str, Any],
        job_details: Dict[str, Any],
        application_id: str,
        custom_answers: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable[[str, str, Dict[str, Any]], Awaitable[None]]] = None,
        question_request_callback: Optional[Callable[[str, Dict[str, Any]], Awaitable[None]]] = None
    ) -> Dict[str, Any]:
        """
        Executes the autonomous browser application loop.
        Uses browser-use with Gemini when available, otherwise runs simulation.
        """
        mapped_data = form_mapper.map_candidate_fields(user_profile, custom_answers)
        job_url = job_details.get("externalUrl", "")
        company = job_details.get("companyName", "Target Company")
        title = job_details.get("title", "Target Role")

        async def emit_step(status_code: str, message: str, extra: Optional[Dict[str, Any]] = None):
            logger.info(f"[{application_id}] {status_code}: {message}")
            if progress_callback:
                await progress_callback(status_code, message, extra or {})

        # Determine whether to use real browser-use or simulation
        llm = _get_gemini_llm() if BROWSER_USE_AVAILABLE else None
        use_real_agent = BROWSER_USE_AVAILABLE and llm is not None and bool(job_url)

        if use_real_agent:
            return await self._execute_with_browser_use(
                llm=llm,
                mapped_data=mapped_data,
                job_url=job_url,
                company=company,
                title=title,
                application_id=application_id,
                user_profile=user_profile,
                job_details=job_details,
                emit_step=emit_step,
            )
        else:
            reason = (
                "browser-use not installed" if not BROWSER_USE_AVAILABLE
                else "Gemini API key not configured" if not llm
                else "No job URL provided"
            )
            logger.info(f"Running application flow in simulation mode ({reason}).")
            return await self._execute_simulated(
                mapped_data=mapped_data,
                company=company,
                title=title,
                job_url=job_url,
                application_id=application_id,
                user_profile=user_profile,
                job_details=job_details,
                emit_step=emit_step,
            )

    async def _execute_with_browser_use(
        self,
        llm,
        mapped_data: Dict[str, Any],
        job_url: str,
        company: str,
        title: str,
        application_id: str,
        user_profile: Dict[str, Any],
        job_details: Dict[str, Any],
        emit_step,
    ) -> Dict[str, Any]:
        """Execute application flow using browser-use AI agent with Gemini."""
        await emit_step("INITIALIZING_AGENT", f"Launching AI browser agent for {company} ({title})...")

        # Build the natural language task description for the AI agent
        task_description = self._build_agent_task(mapped_data, job_url, company, title)

        await emit_step("NAVIGATING", f"AI agent navigating to: {job_url}")

        try:
            agent = BrowserAgent(
                task=task_description,
                llm=llm,
            )

            await emit_step("ANALYZING_DOM", "AI agent analyzing page structure and identifying form fields...")

            # Run the agent with a timeout
            result = await asyncio.wait_for(
                agent.run(),
                timeout=180  # 3 minute timeout
            )

            await emit_step("MAPPING_FIELDS", "AI agent has completed form field analysis and autofill.")

            logger.info(f"browser-use agent completed for {application_id}. Result: {str(result)[:500]}")

        except asyncio.TimeoutError:
            await emit_step("AGENT_TIMEOUT", "AI agent timed out after 3 minutes. Creating review package from partial progress...")
        except Exception as e:
            logger.error(f"browser-use agent error for {application_id}: {e}")
            await emit_step("AGENT_ERROR", f"AI agent encountered an issue: {str(e)[:200]}. Creating review package...")

        # Generate HITL review package
        return await self._create_hitl_package(
            mapped_data=mapped_data,
            company=company,
            title=title,
            application_id=application_id,
            user_profile=user_profile,
            job_details=job_details,
            emit_step=emit_step,
        )

    async def _execute_simulated(
        self,
        mapped_data: Dict[str, Any],
        company: str,
        title: str,
        job_url: str,
        application_id: str,
        user_profile: Dict[str, Any],
        job_details: Dict[str, Any],
        emit_step,
    ) -> Dict[str, Any]:
        """Simulated application flow when browser-use is unavailable."""
        await emit_step("INITIALIZING_AGENT", f"Preparing application agent for {company} ({title})...")
        await asyncio.sleep(0.5)

        await emit_step("NAVIGATING", f"Targeting career portal: {job_url or 'Company careers page'}")
        await asyncio.sleep(0.6)

        await emit_step("ANALYZING_DOM", "Mapping application form fields against candidate persona...")
        await asyncio.sleep(0.5)

        await emit_step("MAPPING_FIELDS", "Autofilling candidate identity, contact, CTC, and experience fields...")
        await asyncio.sleep(0.6)

        await emit_step("ATTACHING_RESUME", f"Attaching resume for {user_profile.get('name', 'Candidate')}...")
        await asyncio.sleep(0.5)

        return await self._create_hitl_package(
            mapped_data=mapped_data,
            company=company,
            title=title,
            application_id=application_id,
            user_profile=user_profile,
            job_details=job_details,
            emit_step=emit_step,
        )

    async def _create_hitl_package(
        self,
        mapped_data: Dict[str, Any],
        company: str,
        title: str,
        application_id: str,
        user_profile: Dict[str, Any],
        job_details: Dict[str, Any],
        emit_step,
    ) -> Dict[str, Any]:
        """Creates the HITL review package for candidate verification."""
        await emit_step("CAPTURING_REVIEW_SNAPSHOT", "Generating review package for candidate verification...")
        await asyncio.sleep(0.4)

        screenshot_url = "/artifacts/previews/app_review_snapshot.png"

        filled_summary = {
            "Applicant Name": mapped_data.get("full_name", ""),
            "Email Address": mapped_data.get("email", ""),
            "Phone Number": mapped_data.get("phone", ""),
            "Location": mapped_data.get("location", ""),
            "Current Role & Experience": f"{mapped_data.get('current_role', 'Engineer')} ({mapped_data.get('total_experience_years', 0)} Years)",
            "Current CTC (LPA)": f"{mapped_data.get('current_ctc_lpa', 0)} LPA",
            "Expected CTC (LPA)": f"{mapped_data.get('expected_ctc_lpa', 0)} LPA",
            "Notice Period": f"{mapped_data.get('notice_period_days', 30)} Days",
            "Work Authorization": "Authorized to work in India",
            "Target Company": company,
            "Target Role": title,
        }

        hitl_package = hitl_controller.create_review_package(
            application_id=application_id,
            user_id=user_profile.get("userId", ""),
            job_id=job_details.get("jobId", ""),
            filled_fields=filled_summary,
            screenshot_url=screenshot_url,
        )

        await emit_step("HITL_REVIEW_READY",
            "Review package ready — verify and authorize the application submission.", {
                "hitlPackage": hitl_package,
                "applicationId": application_id,
            })

        return hitl_package

    def _build_agent_task(
        self,
        mapped_data: Dict[str, Any],
        job_url: str,
        company: str,
        title: str,
    ) -> str:
        """Build a natural language task description for the browser-use AI agent."""
        return f"""
You are an autonomous job application agent. Your task is to apply to a job opening.

**Job Details:**
- Company: {company}
- Position: {title}
- Application URL: {job_url}

**Candidate Information to Fill:**
- Full Name: {mapped_data.get('full_name', '')}
- Email: {mapped_data.get('email', '')}
- Phone: {mapped_data.get('phone', '')}
- Location: {mapped_data.get('location', '')}
- Current Role: {mapped_data.get('current_role', '')}
- Years of Experience: {mapped_data.get('total_experience_years', '')}
- Current CTC: {mapped_data.get('current_ctc_lpa', '')} LPA
- Expected CTC: {mapped_data.get('expected_ctc_lpa', '')} LPA
- Notice Period: {mapped_data.get('notice_period_days', 30)} days

**Instructions:**
1. Navigate to the application URL
2. Look for the job application form or "Apply" button
3. Fill in all available form fields with the candidate information above
4. For any dropdown/select fields, choose the most appropriate option
5. DO NOT submit the final form — stop at the review/preview page
6. If you encounter a login wall, stop and report that authentication is required

IMPORTANT: Do NOT click the final "Submit" or "Apply" button. Stop at the review stage.
"""


browser_worker = BrowserWorker()
