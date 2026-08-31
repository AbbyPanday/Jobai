import pytest
from app.services.search.query_builder import SearchCriteria, build_boolean_query, build_naukri_search_params
from app.services.research.salary_researcher import calculate_indian_monthly_in_hand, research_company_compensation
from app.services.matching.ats_scorer import ats_scorer
from app.services.agent.form_mapper import form_mapper
from app.services.agent.hitl_controller import hitl_controller
from app.core.gcp_clients import db

def test_boolean_query_builder():
    criteria = SearchCriteria(
        titles=["Software Engineer", "Backend Developer"],
        required_skills=["Python", "FastAPI"],
        excluded_keywords=["Intern", "Fresher"]
    )
    query = build_boolean_query(criteria)
    assert '("Software Engineer" OR "Backend Developer")' in query
    assert '("Python" OR "FastAPI")' in query
    assert 'NOT ("Intern" OR "Fresher")' in query

def test_indian_in_hand_calculation():
    # 28 LPA with 80% fixed base (22.4 LPA gross fixed)
    monthly = calculate_indian_monthly_in_hand(28.0, 80.0)
    assert monthly > 100000  # Should be around ~1.25L - 1.45L per month
    assert isinstance(monthly, int)

@pytest.mark.asyncio
async def test_ats_scoring():
    user = {
        "userId": "usr_test",
        "name": "Abhimanyu Panda",
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
    eval_res = await ats_scorer.evaluate_match(user, job)
    assert eval_res.matchScore >= 80.0
    assert eval_res.isHighMatch is True
    assert eval_res.matchBreakdown.hardSkills > 0

def test_hitl_controller_flow():
    app_id = "app_test_99"
    user_id = "usr_test"
    job_id = "job_test_1"
    fields = {"Applicant Name": "Abhimanyu", "Expected CTC": "28 LPA"}
    
    # 1. Create review package
    package = hitl_controller.create_review_package(
        application_id=app_id,
        user_id=user_id,
        job_id=job_id,
        filled_fields=fields,
        screenshot_url="/artifacts/test.png"
    )
    assert "reviewToken" in package
    token = package["reviewToken"]

    # 2. Approve application
    res = hitl_controller.process_user_decision(
        application_id=app_id,
        decision="APPROVE",
        token=token
    )
    assert res["status"] == "SUBMITTED"
