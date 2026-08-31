"""
Integration & Authentication Test Suite
========================================
Tests:
  1. Google Authentication & Candidate User Provisioning
  2. LinkedIn Profile Extraction & Skill Merging
  3. Naukri India Profile Extraction (CTC, Notice Period, Skills)
  4. Integration Status Aggregator
  5. ATS 5-Factor Scorer Integration with Synced Profiles
"""

import sys, os
sys.path.insert(0, r"c:\Users\Admin\Downloads\AbhimanyuCodes\App1\backend")

class DummyPytest:
    class mark:
        @staticmethod
        def asyncio(fn):
            return fn

try:
    import pytest
except ImportError:
    pytest = DummyPytest()

import asyncio
from typing import Dict, Any

from app.core.gcp_clients import db
from app.services.integrations.google_auth import (
    google_auth_service,
    GoogleAuthPayload,
)
from app.services.integrations.linkedin_connector import (
    linkedin_connector,
    LinkedInSyncRequest,
)
from app.services.integrations.naukri_connector import (
    naukri_connector,
    NaukriSyncRequest,
)
from app.services.matching.ats_scorer import ats_scorer


@pytest.mark.asyncio
async def test_google_auth_provisioning():
    """Test candidate authentication and profile provisioning via Google OAuth."""
    payload = GoogleAuthPayload(
        email="abhimanyu.lead@gmail.com",
        name="Abhimanyu Lead Engineer",
        picture="https://example.com/avatar.jpg",
        sub="google_sub_1029384756",
        isMock=True,
    )

    auth_response = await google_auth_service.verify_and_authenticate(payload)

    assert auth_response.success is True
    assert "user_google_sub_1029384756" in auth_response.userId
    assert auth_response.email == "abhimanyu.lead@gmail.com"
    assert auth_response.fullName == "Abhimanyu Lead Engineer"
    assert auth_response.token.startswith("jwt_session_")

    # Verify user saved in DB
    user = db.get_user(auth_response.userId)
    assert user is not None
    assert user["authProvider"] == "GOOGLE"
    assert user["connectedAccounts"]["google"]["connected"] is True


@pytest.mark.asyncio
async def test_linkedin_profile_sync():
    """Test importing and merging candidate skills and headline from LinkedIn."""
    user_id = "test_user_linkedin_sync"
    db.save_user(user_id, {
        "userId": user_id,
        "fullName": "Abhimanyu Tech",
        "skills": {
            "primarySkills": ["Python", "SQL"],
            "secondarySkills": ["Git"],
            "domainExpertise": ["Web Applications"],
        },
        "yearsExperience": 3.0,
    })

    sync_req = LinkedInSyncRequest(
        userId=user_id,
        profileUrl="https://www.linkedin.com/in/abhimanyu-candidate",
        profileText="""
        Senior Backend Architect with 6 years experience building high-throughput microservices.
        Core Skills: Python, FastAPI, Docker, Kubernetes, PostgreSQL, Redis, GCP, Kafka.
        Domain: FinTech, Scalable Distributed Systems.
        """,
    )

    result = await linkedin_connector.sync_profile(sync_req)

    assert result["success"] is True
    updated = result["updatedProfile"]

    # Verify skills were merged
    skills = updated["skills"]
    primary_skills = [s.lower() for s in skills["primarySkills"]]
    assert "python" in primary_skills
    assert "fastapi" in primary_skills or "docker" in primary_skills

    # Verify LinkedIn connection status
    assert updated["connectedAccounts"]["linkedin"]["connected"] is True
    assert updated["connectedAccounts"]["linkedin"]["profileUrl"] == sync_req.profileUrl


@pytest.mark.asyncio
async def test_naukri_profile_sync():
    """Test importing Indian market parameters (Notice Period, CTC) from Naukri."""
    user_id = "test_user_naukri_sync"
    db.save_user(user_id, {
        "userId": user_id,
        "fullName": "Abhimanyu Tech",
        "skills": {
            "primarySkills": ["Python", "FastAPI"],
            "secondarySkills": ["PostgreSQL"],
            "domainExpertise": ["FinTech"],
        },
        "preferences": {
            "preferredLocations": ["Bengaluru"],
            "minCtcLpa": 20.0,
        },
    })

    sync_req = NaukriSyncRequest(
        userId=user_id,
        syncMethod="CREDENTIALS",
        username="abhimanyu-tech",
        profileText="""
        Senior Python Developer with 5 years experience in Django, FastAPI, AWS, Docker.
        Current CTC: 22 LPA, Expected CTC: 32 LPA. Notice Period: 15 Days.
        Preferred Location: Bengaluru, Pune, Remote.
        """,
        noticePeriodDays=15,
        currentCtcLpa=22.0,
        expectedCtcLpa=32.0,
    )

    result = await naukri_connector.sync_profile(sync_req)

    assert result["success"] is True
    updated = result["updatedProfile"]

    # Verify Indian tech market parameters
    assert updated["noticePeriodDays"] == 15
    assert updated["currentCtcLpa"] == 22.0
    assert updated["expectedCtcLpa"] == 32.0
    assert updated["preferences"]["minCtcLpa"] == 32.0
    assert "Bengaluru" in updated["preferences"]["preferredLocations"]

    # Verify Naukri connection status
    assert updated["connectedAccounts"]["naukri"]["connected"] is True


@pytest.mark.asyncio
async def test_synced_profile_ats_evaluation():
    """Test that ATS matching radar accurately evaluates a profile enriched by LinkedIn + Naukri."""
    user_id = "test_user_full_sync"

    # Step 1: Google Auth
    auth_res = await google_auth_service.verify_and_authenticate(GoogleAuthPayload(
        email="candidate.full@gmail.com",
        name="Candidate Full",
        isMock=True,
    ))

    # Step 2: LinkedIn Sync
    await linkedin_connector.sync_profile(LinkedInSyncRequest(
        userId=auth_res.userId,
        profileText="Senior Python Backend Architect. Skills: Python, FastAPI, PostgreSQL, Docker, Kubernetes, GCP.",
    ))

    # Step 3: Naukri Sync
    await naukri_connector.sync_profile(NaukriSyncRequest(
        userId=auth_res.userId,
        noticePeriodDays=15,
        currentCtcLpa=20.0,
        expectedCtcLpa=30.0,
    ))

    synced_user = db.get_user(auth_res.userId)

    # Step 4: Evaluate against target job
    job = {
        "jobId": "job-target-1",
        "title": "Senior Python Backend Engineer",
        "companyName": "TechFin Corp",
        "location": "Bengaluru, Karnataka",
        "description": "Seeking Python Backend Engineer with FastAPI, PostgreSQL, Docker, GCP in Bengaluru. Salary 28-35 LPA.",
        "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "GCP"],
        "experienceYears": 4.0,
        "ctcLpa": 30.0,
        "source": "LINKEDIN",
    }

    match = await ats_scorer.evaluate_match(synced_user, job)

    assert match.matchScore >= 75.0
    assert match.isHighMatch is True
    assert match.matchBreakdown.hardSkills >= 80.0
    assert match.matchBreakdown.locationFit >= 90.0
    assert len(match.strengths) > 0


if __name__ == "__main__":
    async def run_all():
        print("Running Google Auth test...")
        await test_google_auth_provisioning()
        print("[OK] Google Auth passed!")

        print("\nRunning LinkedIn Profile Sync test...")
        await test_linkedin_profile_sync()
        print("[OK] LinkedIn Sync passed!")

        print("\nRunning Naukri Profile Sync test...")
        await test_naukri_profile_sync()
        print("[OK] Naukri Sync passed!")

        print("\nRunning End-to-End ATS Match on Synced Profile...")
        await test_synced_profile_ats_evaluation()
        print("[OK] ATS Match on Synced Profile passed!")

        print("\n================================================")
        print("ALL 4 INTEGRATION TEST SUITES PASSED SUCCESSFULLY!")
        print("================================================")

    asyncio.run(run_all())
