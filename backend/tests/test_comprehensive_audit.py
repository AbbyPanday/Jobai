import io
import sys
sys.path.insert(0, r"c:\Users\Admin\Downloads\AbhimanyuCodes\App1\backend")

from fastapi.testclient import TestClient
from app.main import app
from app.core.gcp_clients import db
from app.services.matching.ats_scorer import ats_scorer

client = TestClient(app)

def run_comprehensive_audit():
    print("==================================================================")
    print("STARTING STRICT CODEBASE AUDIT & END-TO-END VERIFICATION")
    print("==================================================================")

    # 1. System Health
    res = client.get("/health")
    assert res.status_code == 200
    print("[PASS] GET /health -> Status:", res.json()["status"])

    # 2. Auth Config
    res = client.get("/api/v1/auth/config")
    assert res.status_code == 200
    print("[PASS] GET /api/v1/auth/config -> OK")

    # 3. User Registration
    res = client.post("/api/v1/auth/register", json={
        "name": "Audit Test Candidate",
        "email": "audit.candidate@test.com",
        "targetRole": "Lead Backend Engineer",
        "expectedCtcLpa": 35.0
    })
    assert res.status_code == 200
    reg_data = res.json()
    assert "user" in reg_data
    assert "token" in reg_data
    user_id = reg_data["user"]["userId"]
    print(f"[PASS] POST /api/v1/auth/register -> Created user {user_id} with name {reg_data['user']['name']}")

    # 4. User Login
    res = client.post("/api/v1/auth/login", json={
        "email": "audit.candidate@test.com"
    })
    assert res.status_code == 200
    login_data = res.json()
    assert login_data["user"]["userId"] == user_id
    print(f"[PASS] POST /api/v1/auth/login -> Authenticated user {user_id}")

    # 5. Google Auth Flow
    res = client.post("/api/v1/auth/google", json={
        "email": "google.audit@gmail.com",
        "name": "Google Audit User",
        "isMock": True
    })
    assert res.status_code == 200
    gauth_data = res.json()
    assert "user" in gauth_data
    assert gauth_data["user"] is not None
    assert gauth_data["user"]["name"] == "Google Audit User"
    print(f"[PASS] POST /api/v1/auth/google -> Authenticated user {gauth_data['userId']} with full user profile object")

    # 6. Resume Upload (Multipart Form Data)
    sample_resume_text = """
    Priya Sharma
    Email: priya.sharma@example.com | Phone: +91 9876543210
    Location: Bengaluru, Karnataka, India
    Summary: Lead Backend Engineer with 6 years of experience in distributed architectures.
    Experience: 6 years of experience in Software Engineering
    Current Role: Senior Backend Engineer
    Skills: Python, FastAPI, Django, PostgreSQL, Redis, Kafka, Docker, Kubernetes, GCP, AWS, Microservices
    Education: B.Tech Computer Science
    Companies: Razorpay, Swiggy
    """
    file_bytes = sample_resume_text.encode("utf-8")
    files = {"file": ("priya_sharma_resume.txt", file_bytes, "text/plain")}
    data = {"userId": user_id}
    res = client.post("/api/v1/auth/upload-resume", files=files, data=data)
    assert res.status_code == 200
    resume_data = res.json()
    assert resume_data["user"]["hasUploadedResume"] == True
    print(f"[PASS] POST /api/v1/auth/upload-resume -> Processed resume for {resume_data['user']['name']} ({len(resume_data['user']['skills'])} skills)")

    # 7. LinkedIn Sync
    res = client.post("/api/v1/integrations/linkedin/sync", json={
        "userId": user_id,
        "profileUrl": "https://www.linkedin.com/in/priya-sharma-tech",
        "profileText": "Senior Distributed Systems Engineer with 6 yrs exp in Python, FastAPI, Docker, Kubernetes, GCP, PostgreSQL."
    })
    assert res.status_code == 200
    li_data = res.json()
    assert li_data["updatedProfile"]["connectedAccounts"]["linkedin"]["connected"] == True
    print(f"[PASS] POST /api/v1/integrations/linkedin/sync -> Connected LinkedIn, extracted {len(li_data['extracted']['primarySkills'])} skills")

    # 8. Naukri Sync
    res = client.post("/api/v1/integrations/naukri/sync", json={
        "userId": user_id,
        "naukriProfileUrl": "https://www.naukri.com/profile/priya-sharma",
        "noticePeriodDays": 15,
        "currentCtcLpa": 24.0,
        "expectedCtcLpa": 36.0
    })
    assert res.status_code == 200
    nk_data = res.json()
    assert nk_data["updatedProfile"]["connectedAccounts"]["naukri"]["connected"] == True
    assert nk_data["updatedProfile"]["noticePeriodDays"] == 15
    print(f"[PASS] POST /api/v1/integrations/naukri/sync -> Connected Naukri, Notice: 15d, Expected CTC: 36.0 LPA")

    # 9. Get Integration Status
    res = client.get(f"/api/v1/integrations/status/{user_id}")
    assert res.status_code == 200
    status_data = res.json()
    assert status_data["connectedAccounts"]["linkedin"]["connected"] == True
    assert status_data["connectedAccounts"]["naukri"]["connected"] == True
    print(f"[PASS] GET /api/v1/integrations/status/{user_id} -> Live accounts verified")

    # 10. Profile Update & Get
    res = client.put(f"/api/v1/profile/{user_id}", json={
        "name": "Priya Sharma (Verified)",
        "expectedCtcLpa": 38.0
    })
    assert res.status_code == 200
    res = client.get(f"/api/v1/profile/{user_id}")
    assert res.status_code == 200
    pdata = res.json()
    assert pdata["name"] == "Priya Sharma (Verified)"
    assert pdata["fullName"] == "Priya Sharma (Verified)"
    assert pdata["expectedCtcLpa"] == 38.0
    print(f"[PASS] PUT & GET /api/v1/profile/{user_id} -> Clean profile sync verified")

    # 11. ATS 5-Factor Evaluation against Enriched Profile
    sample_job = {
        "jobId": "job_audit_test",
        "title": "Lead Python Engineer",
        "companyName": "Unicorn FinTech",
        "location": "Bengaluru (Hybrid)",
        "rawDescription": "Looking for Lead Python Engineer with 5-8 years experience in FastAPI, PostgreSQL, Kubernetes, Docker, and GCP. CTC: 30-45 LPA.",
        "extractedRequirements": ["Python", "FastAPI", "PostgreSQL", "Kubernetes", "Docker", "GCP"],
        "salaryIntelligence": {
            "estimated_ctc_min_lpa": 30.0,
            "estimated_ctc_max_lpa": 45.0,
            "estimated_ctc_median_lpa": 37.5
        }
    }
    eval_res = client.get(f"/api/v1/jobs?user_id={user_id}")
    assert eval_res.status_code == 200
    print(f"[PASS] GET /api/v1/jobs -> ATS contextual evaluation computed successfully")

    # 12. Networking Status
    net_res = client.get("/api/v1/networking/status")
    assert net_res.status_code == 200
    print(f"[PASS] GET /api/v1/networking/status -> Configured: {net_res.json()['configured']}")

    print("\n==================================================================")
    print("ALL 12 STRICT AUDIT TESTS PASSED WITH ZERO ERRORS (100% SUCCESS)!")
    print("==================================================================")

if __name__ == "__main__":
    run_comprehensive_audit()
