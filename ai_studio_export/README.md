# Google AI Studio Prompt & Evaluation Export Bundle

This bundle contains production-ready system prompts, JSON response schemas, and Indian tech sample test datasets exported directly from the **Job Intelligence & Autonomous Application Engine**.

---

## Folder Structure

- `prompts/`
  - `01_multimodal_resume_parser.json` — ATS Resume Document Parser with Structured Schema
  - `02_compensation_intelligence_grounding.json` — Compensation synthesis with Google Search Grounding (AmbitionBox, Glassdoor India)
  - `03_ats_match_and_gap_evaluator.json` — ATS Match Score, Skill Gap, and Resume Tailoring Evaluator
  - `04_autonomous_application_planner.json` — Browser-Use Form Field Mapper & Action Planner
- `test_datasets/`
  - `sample_resumes.json` — Realistic candidate resumes across Indian Tech roles (SDE-2, Fullstack, DevOps)
  - `sample_job_descriptions.json` — Realistic job postings from top Indian tech companies (Swiggy, Razorpay, CRED, Uber India)
- `scripts/`
  - `run_ai_studio_tests.py` — Automated verification script using the `google-genai` SDK

---

## How to Import into Google AI Studio (aistudio.google.com)

1. **Open Google AI Studio**: Go to [aistudio.google.com](https://aistudio.google.com/).
2. **Create a New Prompt**: Click **"Create Prompt"** (Chat or Structured).
3. **Select Model**: Choose `gemini-2.5-flash` or `gemini-2.5-pro`.
4. **Configure System Instructions**: Copy the `system_instructions` text from the corresponding prompt JSON file.
5. **Configure Structured Output**: In the right sidebar under **"Output format"**, select **JSON Schema** and paste the `response_schema` object.
6. **Enable Tools**: For prompt `02_compensation_intelligence_grounding.json`, enable the **Google Search** toggle in the right sidebar.
7. **Test with Sample Data**: Copy user prompts from `test_datasets/` to test live inference.
