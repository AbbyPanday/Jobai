import sys
import os
import json
import time
import urllib.request
import urllib.error

# Ensure stdout handles UTF-8 on Windows
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8")

SERVER_BASE = "http://127.0.0.1:8000"
API_BASE = f"{SERVER_BASE}/api/v1"

def log_section(title):
    print("\n" + "=" * 60)
    print(f"  [TEST] {title}")
    print("=" * 60)

def make_request(method, endpoint, data=None, headers=None, is_root=False):
    url = f"{SERVER_BASE}{endpoint}" if is_root else f"{API_BASE}{endpoint}"
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)

    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=req_headers, method=method)
    
    try:
        with urllib.request.urlopen(req) as resp:
            resp_body = resp.read().decode("utf-8")
            return resp.getcode(), json.loads(resp_body) if resp_body else {}
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        try:
            return e.code, json.loads(err_body)
        except Exception:
            return e.code, {"error": err_body}
    except Exception as ex:
        return 0, {"exception": str(ex)}

def test_health():
    log_section("1. System Health & Gateway Root")
    code, res = make_request("GET", "/health", is_root=True)
    assert code == 200, f"Health check failed: {code} {res}"
    print(f"  [PASS] Health Check: {res}")

    code_root, res_root = make_request("GET", "/", is_root=True)
    assert code_root == 200, f"Root check failed: {code_root} {res_root}"
    print(f"  [PASS] Gateway Root: {res_root}")

def test_auth_flows():
    log_section("2. Google OAuth & Email/Password Auth")
    
    # 1. Google OAuth Sign In
    code, google_res = make_request("POST", "/auth/google", {
        "email": "lead.engineer@example.com",
        "name": "Arjun Mehta",
        "googleId": "gid_google_98765"
    })
    assert code == 200, f"Google auth failed: {code} {google_res}"
    token = google_res["token"]
    user_id = google_res["user"]["userId"]
    print(f"  [PASS] Google Auth Success | UserID: {user_id} | Token: {token[:12]}...")

    # 2. Session verification (/auth/me)
    code, me_res = make_request("GET", "/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert code == 200 and me_res["authenticated"], f"Auth me verification failed: {code} {me_res}"
    print(f"  [PASS] Session Token Verified: {me_res['user']['name']} ({me_res['user']['email']})")

    # 3. Email Register
    code, reg_res = make_request("POST", "/auth/register", {
        "name": "Kavita Rao",
        "email": f"kavita.{int(time.time())}@example.com",
        "password": "Password@123",
        "targetRole": "Staff Backend Engineer",
        "expectedCtcLpa": 42.0
    })
    assert code == 200, f"Email registration failed: {code} {reg_res}"
    print(f"  [PASS] Email Registration Success: {reg_res['user']['name']} | Expected CTC: INR {reg_res['user']['expectedCtcLpa']} LPA")

    return token, user_id

def test_job_search_and_ingestion(user_id):
    log_section("3. Boolean Query Search & Job Ingestion")

    criteria = {
        "titles": ["Lead Backend Engineer", "Distributed Systems Architect"],
        "required_skills": ["Python", "FastAPI", "GCP", "Kubernetes", "Kafka"],
        "optional_skills": ["Redis", "PostgreSQL"],
        "excluded_keywords": ["Intern", "Junior"],
        "locations": ["Bengaluru", "Hyderabad", "Remote"],
        "min_exp_years": 4,
        "max_exp_years": 8
    }

    code, jobs = make_request("POST", "/jobs/ingest", {"criteria": criteria})
    assert code == 200 and isinstance(jobs, list) and len(jobs) > 0, f"Job ingestion failed: {code} {jobs}"
    print(f"  [PASS] Ingestion Complete: {len(jobs)} high-value jobs ingested and indexed.")

    # Test GET /jobs with user scoring
    code, user_jobs = make_request("GET", f"/jobs?user_id={user_id}&min_match=0")
    assert code == 200 and len(user_jobs) > 0, f"Get jobs with ATS scoring failed: {code} {user_jobs}"
    top_job = user_jobs[0]
    print(f"  [PASS] Top Job: '{top_job['title']}' at {top_job['companyName']} (Match: {top_job.get('matchScore', 0)}%)")

    return top_job["jobId"]

def test_salary_intelligence():
    log_section("4. AmbitionBox & Glassdoor Compensation Intelligence")

    code, salary_data = make_request(
        "GET",
        "/jobs/research/salary?company=Swiggy&role=Senior+Backend+Engineer&exp_years=5"
    )
    assert code == 200, f"Salary research failed: {code} {salary_data}"
    
    print(f"  [PASS] Company: {salary_data['company_name']} | Role: {salary_data['designation']}")
    print(f"  [PASS] Estimated CTC Bracket: INR {salary_data['estimated_ctc_min_lpa']} - {salary_data['estimated_ctc_max_lpa']} LPA (Median: INR {salary_data['estimated_ctc_median_lpa']} LPA)")
    print(f"  [PASS] Monthly In-Hand (New Tax Regime): INR {salary_data.get('monthly_in_hand_median_inr', 0):,}/month")
    print(f"  [PASS] AmbitionBox Rating: {salary_data['ambitionbox_rating']}/5 | Glassdoor: {salary_data['glassdoor_rating']}/5")
    print(f"  [PASS] Negotiation Leverage: {salary_data['negotiation_leverage_tips'][0]}")

def test_profile_management(user_id):
    log_section("5. Candidate Profile & Preference Updates")

    # Fetch profile
    code, profile = make_request("GET", f"/profile/{user_id}")
    assert code == 200, f"Fetch profile failed: {code} {profile}"

    # Update profile
    updates = {
        "skills": ["Python", "FastAPI", "GCP", "PostgreSQL", "Kafka", "Kubernetes"],
        "expectedCtcLpa": 38.0,
        "noticePeriodDays": 15,
        "autoApplyThreshold": 85.0
    }
    code, updated = make_request("PUT", f"/profile/{user_id}", updates)
    assert code == 200, f"Update profile failed: {code} {updated}"
    assert updated["expectedCtcLpa"] == 38.0
    assert updated["noticePeriodDays"] == 15
    print(f"  [PASS] Candidate Profile Updated: Expected CTC: INR {updated['expectedCtcLpa']} LPA | Notice: {updated['noticePeriodDays']} days | Skills: {len(updated['skills'])}")

def test_application_and_hitl_pipeline(user_id, job_id):
    log_section("6. Autonomous Apply & HITL Gate Decision")

    # 1. Trigger Apply
    code, app_res = make_request("POST", "/applications/apply", {
        "jobId": job_id,
        "userId": user_id
    })
    assert code == 200, f"Apply endpoint failed: {code} {app_res}"
    app_id = app_res["applicationId"]
    status = app_res["status"]
    print(f"  [PASS] Application Triggered: ID: {app_id} | Initial Status: {status}")

    # 2. Get Applications list
    code, apps = make_request("GET", f"/applications?user_id={user_id}")
    assert code == 200 and len(apps) > 0, f"Get applications failed: {code} {apps}"
    target_app = next((a for a in apps if a["applicationId"] == app_id), None)
    assert target_app is not None, "Application not found in user pipeline"
    print(f"  [PASS] Application Pipeline Verified: Found {len(apps)} active records.")

    # 3. Simulate HITL Approval decision
    review_data = target_app.get("hitlReviewData")
    token = review_data.get("reviewToken") if review_data else "test_token_valid"
    code, decision_res = make_request("POST", f"/applications/{app_id}/decision", {
        "decision": "APPROVE",
        "token": token
    })
    assert code == 200, f"HITL decision failed: {code} {decision_res}"
    print(f"  [PASS] HITL Decision Dispatched: Status -> {decision_res['status']}")

if __name__ == "__main__":
    print("\nSTARTING COMPREHENSIVE BACKEND & ENDPOINT AUDIT...")
    try:
        test_health()
        auth_token, user_id = test_auth_flows()
        job_id = test_job_search_and_ingestion(user_id)
        test_salary_intelligence()
        test_profile_management(user_id)
        test_application_and_hitl_pipeline(user_id, job_id)
        print("\n" + "=" * 60)
        print("  ALL 6/6 BACKEND MODULE AUDITS PASSED WITH ZERO ERRORS!")
        print("=" * 60 + "\n")
    except AssertionError as e:
        print(f"\n[FAIL] AUDIT ASSERTION FAILED: {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n[FAIL] AUDIT UNEXPECTED ERROR: {e}\n")
        sys.exit(1)
