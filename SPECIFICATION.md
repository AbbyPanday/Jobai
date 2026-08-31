# System Architecture & Technical Specification: Next-Gen Autonomous Job Intelligence & Application Engine (India Focus)

## 1. Executive Summary & Vision

Job seekers in India face two critical structural hurdles:

1. **Information Asymmetry in Compensation & Negotiation:** Vast salary discrepancies exist for identical designations within the same organization due to opaque compensation budgets, variable pay structures (CTC vs. in-hand, ESOP vesting), and negotiation dynamics.
2. **Application Inefficiency & ATS Bottlenecks:** Job seekers spend hundreds of hours manually searching across fragmented portals (Naukri, LinkedIn, Workday, Greenhouse), navigating diverse career portal authentication flows, and filling repetitive forms.

This platform is a **real-time AI-native job intelligence and autonomous application platform** built on **Google Cloud Platform (GCP)** and the **Google Gen AI SDK**. It ingests live job listings, executes deep compensation research across AmbitionBox, Glassdoor, and public intelligence, computes semantic resume match scores, and uses a **Gemini-powered Computer-Use / Playwright Autonomous Agent** with **Human-in-the-Loop (HITL)** verification to apply to high-match jobs on behalf of the user.

---

## 2. System Architecture & High-Level Topology

```
                                  +-------------------------------------------------------------+
                                  |                      Next.js 15 Frontend                    |
                                  |  (Live Dashboard, Match Feed, HITL Review Modal, Chat UI)   |
                                  +------------------------------+------------------------------+
                                                                 |
                                                REST / WebSocket (Bidirectional)
                                                                 |
                                  +------------------------------v------------------------------+
                                  |             Backend API Gateway (Cloud Run)                 |
                                  |         FastAPI (Async Python 3.11+) / Fastify TS           |
                                  +---+--------------------------+--------------------------+---+
                                      |                          |                          |
               +----------------------+                          |                          +----------------------+
               |                                                 |                                                 |
+--------------v---------------+              +------------------v-----------------+              +----------------v---------------+
|    Job Ingestion Engine      |              |   Deep Research & Salary Engine    |              |   Autonomous Application Agent |
| - Boolean / Advanced Search  |              | - Google Search Grounding          |              | - Playwright Browser Worker    |
| - LinkedIn & Naukri Workers  |              | - AmbitionBox & Glassdoor Scraping |              | - Gemini Multimodal Vision     |
| - Google Search Live Feed    |              | - CTC / ESOP / Band Decomposition  |              | - Interactive Q&A via Chat     |
+--------------+---------------+              +------------------+-----------------+              +----------------+---------------+
               |                                                 |                                                 |
               +-------------------------------------------------+-------------------------------------------------+
                                                                 |
                                              Cloud Pub/Sub & Redis Queue (Memorystore)
                                                                 |
                                  +------------------------------v------------------------------+
                                  |                     Google Cloud Platform                   |
                                  |  - Cloud Run (Services & Event-driven Workers)              |
                                  |  - Cloud Firestore (Real-time DB with snapshot listeners)   |
                                  |  - Cloud Storage (Resumes, Screenshots, Artifacts)          |
                                  |  - Secret Manager (Auth tokens, OAuth credentials)          |
                                  |  - Gemini 3.7 Flash  (Google Gen AI SDK)                    |
                                  +-------------------------------------------------------------+

```

---

## 3. Technology Stack & SDK Specifications

### 3.1 Backend Core & Google Cloud Services

* **Language & Runtime:** Python 3.11+ (FastAPI, Asyncio, Pydantic v2) or Node.js 20+ (TypeScript, Fastify).
* **AI & LLM Orchestration:** `google-genai` SDK (`gemini-2.5-flash` / `gemini-3.7-flash` for high-throughput extraction/matching, `gemini-2.5-pro` / `gemini-3.7-flash` for deep compensation synthesis and complex form field mapping).
* **Browser Automation & Vision:** Playwright (Python async API), headless Chromium containerized on Cloud Run (with minimum 2GB RAM / 2 vCPU per instance).
* **Live Ingestion & Message Queue:** Google Cloud Pub/Sub (`google-cloud-pubsub`), Redis (Google Cloud Memorystore) for session cache, sliding windows, and rate-limiting.
* **Storage & Persistence:**
* Google Cloud Firestore (`google-cloud-firestore`): User profiles, indexed jobs, match scores, real-time application states.
* Google Cloud Storage (`google-cloud-storage`): Raw resumes, parsed JSON artifacts, submission proof screenshots.
* **Hosting & Orchestration:** Google Cloud Run (WebSocket and HTTP/2 enabled, session affinity enabled).

### 3.2 Frontend & UI/UX

* **Framework:** Next.js 15 (App Router, Server Actions, React 19).
* **Styling:** Vanilla CSS / Tailwind CSS, Radix UI / Lucide React.
* **State & Data Fetching:** TanStack Query v5, Firestore Client SDK (for real-time snapshot subscriptions), WebSocket Client with exponential backoff.
* **Visualization:** Modern interactive visual charts (for salary band distributions and skill radar charts).

---

## 4. Core Functional Modules

### 4.1 Boolean / Advanced Job Search Engine (LinkedIn + Naukri + Google Search)

The engine converts user preferences into target boolean search syntax (AND, OR, NOT, grouping with parentheses, title operators) to extract targeted listings:

* **LinkedIn Boolean Syntax:** `("Software Engineer" OR "Backend Developer") AND ("FastAPI" OR "Node.js") AND ("GCP" OR "AWS") NOT ("Intern" OR "Lead")`
* **Naukri Key-skills & CTC Matrix:** Queries Naukri search APIs/scrapers by injecting experience ranges (e.g., `3-6 years`), target locations (Bangalore, Pune, Hyderabad, Remote), and designation variants.
* **Google Search Live Discovery:** Employs Google Search Grounding to discover unlisted/off-market positions, newly published career pages, and hiring manager posts (`site:linkedin.com/posts "hiring" "backend" "Bangalore"`).

```python
# app/services/search/query_builder.py
from pydantic import BaseModel
from typing import List

class SearchCriteria(BaseModel):
    titles: List[str]
    required_skills: List[str]
    optional_skills: List[str]
    excluded_keywords: List[str]
    locations: List[str]
    min_exp_years: int
    max_exp_years: int

def build_boolean_query(criteria: SearchCriteria) -> str:
    title_group = f"({' OR '.join([f'\"{t}\"' for t in criteria.titles])})"
    must_have_group = f"({' OR '.join([f'\"{s}\"' for s in criteria.required_skills])})" if criteria.required_skills else ""
    exclude_group = f"NOT ({' OR '.join([f'\"{e}\"' for e in criteria.excluded_keywords])})" if criteria.excluded_keywords else ""
    
    parts = [p for p in [title_group, must_have_group, exclude_group] if p]
    return " AND ".join(parts)
```

---

### 4.2 Deep Company & Salary Intelligence Engine

To counteract negotiation opacity in the Indian market, this module extracts, aggregates, and decomposes compensation structures prior to applying:

1. **Sources Ingested:** AmbitionBox, Glassdoor India, Levels.fyi (India datasets), LeetCode Compensation forums, and public filings.
2. **Gemini Search Grounding:** Performs automated grounded research for the specific company, designation, and year of experience.
3. **CTC Breakdown & Analysis:**
* **Base Pay (Fixed in-hand estimate):** Factoring standard Indian tax slabs and PF deductions.
* **Variable Pay / Performance Bonus:** Typical payout percentages.
* **ESOPs / Stocks:** Vesting period (e.g., 4-year standard with 1-year cliff).
* **Culture & Glassdoor/AmbitionBox Metrics:** Work-life balance rating, promotion velocity, management sentiment.

```python
# app/services/research/salary_researcher.py
from google import genai
from google.genai import types
from pydantic import BaseModel
from typing import Optional, List

class SalaryIntelligenceReport(BaseModel):
    company_name: str
    designation: str
    experience_bracket: str
    estimated_ctc_min_lpa: float
    estimated_ctc_max_lpa: float
    estimated_ctc_median_lpa: float
    fixed_base_percentage: float
    variable_pay_details: str
    esop_details: Optional[str]
    ambitionbox_rating: float
    glassdoor_rating: float
    pros_summary: List[str]
    cons_summary: List[str]
    negotiation_leverage_tips: List[str]

async def research_company_compensation(client: genai.Client, company: str, role: str, exp_years: int) -> SalaryIntelligenceReport:
    prompt = f"""
    Perform deep technical and market research on the Indian salary band for:
    Company: {company}
    Role: {role}
    Experience Level: {exp_years} years
    
    Retrieve and synthesize data from AmbitionBox, Glassdoor, and recent compensation trends in India (in LPA - Lakhs Per Annum).
    Break down fixed vs. variable pay, ESOP trends, work culture pros and cons, and negotiation leverage.
    """
    
    response = client.models.generate_content(
        model="gemini-3.7-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[{"google_search": {}}],
            response_mime_type="application/json",
            response_schema=SalaryIntelligenceReport,
            temperature=0.2,
        ),
    )
    return SalaryIntelligenceReport.model_validate_json(response.text)
```

---

### 4.3 Resume Parsing & ATS Match Scoring Engine

* **Multimodal Document Parser:** Parses PDF/DOCX resumes into structured schema (experience timeline, tech stack, achievements, education, soft skills).
* **Persona Enrichment:** Combines the extracted resume with extra skills/certifications the user provided on their profile.
* **Match Evaluation:** Gemini computes a deterministic match score (0–100%) against the Job Description (JD):
* **Hard Skills Match (40% weight):** Critical tech stack required.
* **Experience & Domain Fit (30% weight):** Depth of past projects and scale.
* **Role Specifics / Secondary Skills (20% weight):** Cloud platforms, tooling, testing.
* **Soft Skills & Education (10% weight):** Degrees, communication, leadership.
* **Threshold Trigger:** If `match_score >= 80%`, the job is marked as **High Match** and immediately pushed to the user via WebSocket/Chat for application approval.

---

### 4.4 Autonomous Browser Agent (Computer-Use / Playwright + Gemini)

When the user approves an application:

```
[Job Match >= 80%]
       |
       v
[User Confirms via Chat / WebSocket]
       |
       v
[Agent Initializes Playwright Worker]
       |
       +---> Navigate to Job / Career Portal (Workday / Greenhouse / Lever / Direct)
       +---> Check Auth Status / Session Cookie
       +---> Read DOM & Screenshot Page
       +---> Gemini 2.0/3.7 Multimodal Analyzes Form Fields
       +---> Autofill known fields from Master Persona
       |
       |---> [Unknown Question Encountered? (e.g., Notice Period, Expected CTC)]
       |           |
       |           v
       |     [Prompt User in Real-Time Live Chat]
       |           |
       |           v
       |     [User Replies -> Agent Fills Field & Saves to Persona]
       |
       v
[Agent Completes Form -> Freezes at Review Screen]
       |
       v
[HITL Gate: Capture Screenshot & Summary -> Send to User for 1-Click Verification]
       |
       +---> [Approved] ---> Submit Application -> Record Confirmation ID & Proof Screenshot
       +---> [Rejected/Edited] ---> Abort or Adjust Fields
```

#### Playwright + Multimodal Vision Implementation Strategy:

* **DOM State Inspection:** Agent extracts interactive elements (`<input>`, `<select>`, `<button>`, `role="combobox"`).
* **Gemini Multimodal Vision Fallback:** For complex non-standard canvases or shadow DOM forms, the worker captures full-page viewport screenshots, sends them to Gemini Vision, and receives coordinates for bounding-box clicks and keyboard inputs.
* **Human-in-the-Loop (HITL) Gate:** The agent never clicks the final `Submit` button without an explicit user confirmation token generated from the review preview card.

---

## 5. Firestore Database Schemas

### `users/{userId}`

```json
{
  "userId": "usr_99812",
  "name": "Abhimanyu Panda",
  "email": "user@domain.com",
  "phone": "+91-XXXXXXXXXX",
  "location": "Pune, Maharashtra, India",
  "currentRole": "Software Engineer",
  "experienceYears": 4.5,
  "currentCtcLpa": 18.0,
  "expectedCtcLpa": 28.0,
  "noticePeriodDays": 30,
  "skills": ["Python", "FastAPI", "GCP", "Kubernetes", "PostgreSQL", "Next.js"],
  "additionalSkills": ["System Design", "Cloud Run", "Gemini API"],
  "linkedInConnected": true,
  "naukriConnected": true,
  "autoApplyThreshold": 80,
  "createdAt": "2026-08-20T10:00:00Z"
}
```

### `jobs/{jobId}`

```json
{
  "jobId": "job_in_77819",
  "source": "LINKEDIN",
  "externalUrl": "https://www.linkedin.com/jobs/view/...",
  "companyName": "TechCorp India",
  "title": "Senior Backend Engineer - Python/GCP",
  "location": "Bengaluru (Hybrid)",
  "rawDescription": "Full JD text...",
  "salaryIntelligence": {
    "minLpa": 26.0,
    "maxLpa": 36.0,
    "medianLpa": 31.0,
    "glassdoorRating": 4.2,
    "ambitionboxRating": 4.1
  },
  "extractedRequirements": ["Python", "FastAPI", "GCP", "Distributed Systems"],
  "postedAt": "2026-08-19T14:30:00Z"
}
```

### `applications/{applicationId}`

```json
{
  "applicationId": "app_55410",
  "userId": "usr_99812",
  "jobId": "job_in_77819",
  "matchScore": 88.5,
  "matchBreakdown": {
    "hardSkills": 92.0,
    "experienceFit": 85.0,
    "domainFit": 88.0
  },
  "status": "AWAITING_HITL_APPROVAL",
  "statusHistory": [
    { "status": "MATCH_FOUND", "timestamp": "2026-08-20T10:05:00Z" },
    { "status": "AGENT_FORM_FILLED", "timestamp": "2026-08-20T10:07:30Z" },
    { "status": "AWAITING_HITL_APPROVAL", "timestamp": "2026-08-20T10:07:32Z" }
  ],
  "hitlReviewData": {
    "screenshotStorageUrl": "gs://bucket-name/previews/app_55410_review.png",
    "filledFieldsSummary": {
      "fullName": "Abhimanyu Panda",
      "noticePeriod": "30 Days",
      "expectedCTC": "28 LPA",
      "resumeUsed": "Abhimanyu_Resume_v4.pdf"
    }
  },
  "submissionProofUrl": null,
  "createdAt": "2026-08-20T10:05:00Z"
}
```

---

## 6. Real-time WebSocket Protocol Specification

The frontend connects to `/ws/agent-feed/{userId}` for live status streaming and two-way interaction with the agent during applications.

### 6.1 Server-to-Client Events

* `JOB_MATCH_DISCOVERED`: Alerts client when a new job with `>= 80%` match is found.
* `AGENT_STATUS_UPDATE`: Emits progress steps (`"Navigating to career portal"`, `"Uploading resume"`, `"Mapping form fields"`).
* `AGENT_QUESTION_REQUEST`: Dispatched when the browser agent needs user input for a question not in the profile.
* `HITL_REVIEW_READY`: Pushes the review screenshot, fields summary, and token for 1-click submission.

### 6.2 Client-to-Server Events

* `ANSWER_QUESTION`: Supplies the missing value and saves it to user persona.
* `HITL_DECISION`: `{ applicationId: string, decision: "APPROVE" | "REJECT", token: string }`.
* `TRIGGER_MANUAL_APPLY`: Initiates agent pipeline for a job manually clicked from the dashboard.

---

## 7. Project Directory Structure

```
autonomous-job-agent/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes_jobs.py
│   │   │   ├── routes_applications.py
│   │   │   ├── routes_profile.py
│   │   │   └── websocket_agent.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── gcp_clients.py
│   │   │   └── security.py
│   │   ├── services/
│   │   │   ├── search/
│   │   │   │   ├── query_builder.py
│   │   │   │   ├── linkedin_worker.py
│   │   │   │   ├── naukri_worker.py
│   │   │   │   └── google_search_worker.py
│   │   ├── services/
│   │   │   ├── research/
│   │   │   │   └── salary_researcher.py
│   │   ├── services/
│   │   │   ├── matching/
│   │   │   │   ├── resume_parser.py
│   │   │   │   └── ats_scorer.py
│   │   └── services/
│   │       └── agent/
│   │           ├── browser_worker.py
│   │           ├── form_mapper.py
│   │           └── hitl_controller.py
│   │   └── main.py
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── dashboard/page.tsx
│   │   │   ├── matches/page.tsx
│   │   │   ├── applications/page.tsx
│   │   │   └── layout.tsx
│   │   ├── components/
│   │   │   ├── LiveChatAgent.tsx
│   │   │   ├── HitlReviewModal.tsx
│   │   │   ├── SalaryBandChart.tsx
│   │   │   ├── JobCard.tsx
│   │   │   └── MatchRadar.tsx
│   │   ├── hooks/
│   │   │   ├── useAgentSocket.ts
│   │   │   └── useFirestoreLive.ts
│   │   └── lib/
│   │       └── firebase.ts
│   ├── package.json
│   └── tailwind.config.js
└── deployment/
    ├── cloudbuild.yaml
    └── deploy.sh
```

---

## 8. Deployment & Cloud Build Configuration

### 8.1 Backend Dockerfile (with Playwright & Chromium)

```dockerfile
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PORT=8080

WORKDIR /app

# Install system dependencies for Playwright Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium --with-deps

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "2"]
```

### 8.2 Google Cloud Run Deployment Script (`deploy.sh`)

```bash
#!/bin/bash
set -e

PROJECT_ID="your-gcp-project-id"
REGION="asia-south1" # Mumbai / Pune region for low latency in India
SERVICE_NAME="job-agent-backend"

echo "Deploying ${SERVICE_NAME} to Cloud Run in ${REGION}..."

gcloud run deploy ${SERVICE_NAME} \
    --source=./backend \
    --project=${PROJECT_ID} \
    --region=${REGION} \
    --platform=managed \
    --memory=2Gi \
    --cpu=2 \
    --min-instances=1 \
    --max-instances=10 \
    --timeout=300 \
    --session-affinity \
    --allow-unauthenticated \
    --set-env-vars="GCP_PROJECT_ID=${PROJECT_ID},GEMINI_MODEL=gemini-2.0-flash"
```

---

## 9. Implementation Roadmap & Milestones

1. **Milestone 1: Ingestion & Intelligence Pipeline (Days 1–3)**
* Set up `google-genai` SDK with Google Search Grounding for salary intelligence.
* Build Boolean search query generator and initial LinkedIn/Naukri/Google Search scrapers.
* Deploy Firestore schemas and document parsers.

2. **Milestone 2: ATS Resume Matching & Scoring Engine (Days 4–5)**
* Implement PDF/DOCX resume upload to Cloud Storage.
* Implement Gemini-based semantic matching logic with structured score breakdown.

3. **Milestone 3: Autonomous Playwright Browser Agent + HITL (Days 6–9)**
* Develop containerized Playwright worker on Cloud Run.
* Implement dynamic form-field mapping with Gemini.
* Build interactive Q&A loop via WebSockets for unknown fields.
* Implement screenshot capture and HITL verification gate.

4. **Milestone 4: Next.js Real-time Dashboard & Chat Integration (Days 10–12)**
* Develop live job feed, salary charts, and status tracking cards.
* Integrate agent chat drawer with real-time streaming notifications.
* Perform end-to-end testing across Workday, Greenhouse, and LinkedIn Easy Apply flows.
