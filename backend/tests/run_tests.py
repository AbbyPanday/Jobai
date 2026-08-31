import sys
import os
import asyncio
import unittest

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.search.query_builder import SearchCriteria, build_boolean_query
from app.services.research.salary_researcher import calculate_indian_monthly_in_hand
from app.services.matching.ats_scorer import ats_scorer
from app.services.agent.hitl_controller import hitl_controller
from app.api.routes_auth import (
    login_with_google,
    GoogleAuthPayload,
    login_user,
    LoginPayload,
    register_user,
    RegisterPayload
)

class TestJobAgentEngine(unittest.TestCase):
    def test_boolean_query_builder(self):
        criteria = SearchCriteria(
            titles=["Software Engineer", "Backend Developer"],
            required_skills=["Python", "FastAPI"],
            excluded_keywords=["Intern", "Fresher"]
        )
        query = build_boolean_query(criteria)
        self.assertIn('("Software Engineer" OR "Backend Developer")', query)
        self.assertIn('("Python" OR "FastAPI")', query)
        self.assertIn('NOT ("Intern" OR "Fresher")', query)
        print("[PASS] test_boolean_query_builder passed")

    def test_indian_in_hand_calculation(self):
        monthly = calculate_indian_monthly_in_hand(28.0, 80.0)
        self.assertTrue(monthly > 100000)
        self.assertIsInstance(monthly, int)
        print(f"[PASS] test_indian_in_hand_calculation passed (Monthly in-hand for 28 LPA: INR {monthly:,})")

    def test_ats_scoring(self):
        user = {
            "userId": "usr_test",
            "name": "Candidate Name",
            "currentRole": "Software Engineer",
            "experienceYears": 4.5,
            "skills": ["Python", "FastAPI", "GCP", "PostgreSQL"],
            "additionalSkills": ["Redis", "Docker"],
            "autoApplyThreshold": 80.0
        }
        job = {
            "jobId": "job_test_1",
            "companyName": "TechCorp",
            "title": "Senior Backend Developer",
            "extractedRequirements": ["Python", "FastAPI", "GCP", "PostgreSQL"],
            "rawDescription": "Looking for Python FastAPI engineer on GCP"
        }
        eval_res = asyncio.run(ats_scorer.evaluate_match(user, job))
        self.assertTrue(eval_res.matchScore >= 80.0)
        self.assertTrue(eval_res.isHighMatch)
        self.assertTrue(eval_res.matchBreakdown.hardSkills > 0)
        print(f"[PASS] test_ats_scoring passed (Match score: {eval_res.matchScore}%, isHighMatch: {eval_res.isHighMatch})")

    def test_hitl_controller_flow(self):
        app_id = "app_test_99"
        user_id = "usr_test"
        job_id = "job_test_1"
        fields = {"Applicant Name": "Candidate", "Expected CTC": "28 LPA"}
        
        # 1. Create review package
        package = hitl_controller.create_review_package(
            application_id=app_id,
            user_id=user_id,
            job_id=job_id,
            filled_fields=fields,
            screenshot_url="/artifacts/test.png"
        )
        self.assertIn("reviewToken", package)
        token = package["reviewToken"]

        # 2. Approve application
        res = hitl_controller.process_user_decision(
            application_id=app_id,
            decision="APPROVE",
            token=token
        )
        self.assertEqual(res["status"], "SUBMITTED")
        print(f"[PASS] test_hitl_controller_flow passed (Status: {res['status']}, Token: {token[:12]}...)")

    def test_google_and_email_auth(self):
        # 1. Test Google OAuth
        google_res = asyncio.run(login_with_google(GoogleAuthPayload(
            email="candidate.google@example.com",
            name="Google Candidate",
            isMock=True
        )))
        self.assertTrue(len(google_res.token) > 0)
        self.assertEqual(google_res.email, "candidate.google@example.com")
        print(f"[PASS] test_google_auth passed (User ID: {google_res.userId})")

        # 2. Test Email Registration
        reg_res = asyncio.run(register_user(RegisterPayload(
            name="Direct Candidate",
            email="direct.candidate@example.com",
            password="securepassword123",
            targetRole="Senior Backend Engineer",
            expectedCtcLpa=28.0
        )))
        self.assertTrue(len(reg_res["token"]) > 0)
        self.assertEqual(reg_res["user"]["name"], "Direct Candidate")
        print(f"[PASS] test_email_register passed (User: {reg_res['user']['name']})")

        # 3. Test Email Login
        login_res = asyncio.run(login_user(LoginPayload(
            email="direct.candidate@example.com",
            password="securepassword123"
        )))
        self.assertTrue(len(login_res["token"]) > 0)
        self.assertEqual(login_res["user"]["name"], "Direct Candidate")
        print(f"[PASS] test_email_login passed (User: {login_res['user']['name']})")

if __name__ == '__main__':
    unittest.main()
