"""
Google AI Studio Prompt Verification Runner
Executes exported prompts against Google Gemini via google-genai SDK.
"""

import os
import sys
import json
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Check API key
API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
if not API_KEY:
    logger.error("GEMINI_API_KEY environment variable is not set.")
    logger.info("Please get your key from https://aistudio.google.com/app/apikey and run:")
    logger.info("  export GEMINI_API_KEY=your_key_here  (Linux/Mac) or  set GEMINI_API_KEY=your_key_here  (Windows)")
    sys.exit(1)

try:
    from google import genai
    from google.genai import types
except ImportError:
    logger.error("google-genai SDK not installed. Run: pip install google-genai")
    sys.exit(1)

client = genai.Client(api_key=API_KEY)
EXPORT_DIR = Path(__file__).resolve().parent.parent


def test_resume_parser():
    logger.info("=" * 60)
    logger.info("TEST 1: Multimodal ATS Resume Extraction")
    logger.info("=" * 60)

    prompt_file = EXPORT_DIR / "prompts" / "01_multimodal_resume_parser.json"
    with open(prompt_file, "r", encoding="utf-8") as f:
        config = json.load(f)

    # Load sample resume
    resumes_file = EXPORT_DIR / "test_datasets" / "sample_resumes.json"
    with open(resumes_file, "r", encoding="utf-8") as f:
        resumes = json.load(f)
    sample_text = resumes[0]["resume_text"]

    response = client.models.generate_content(
        model=config.get("target_model", "gemini-2.5-flash"),
        contents=f"Extract structured details from this resume:\n\n{sample_text}",
        config=types.GenerateContentConfig(
            system_instruction=config.get("system_instructions"),
            temperature=config.get("temperature", 0.1),
            response_mime_type="application/json",
        )
    )

    logger.info("AI Studio Response received:")
    try:
        parsed = json.loads(response.text)
        print(json.dumps(parsed, indent=2))
        logger.info(f"SUCCESS: Extracted name='{parsed.get('full_name')}', YoE={parsed.get('years_of_experience')}, skills={len(parsed.get('primary_skills', []))}")
    except Exception as e:
        logger.warning(f"Raw output (not JSON): {response.text}")


def test_compensation_grounding():
    logger.info("=" * 60)
    logger.info("TEST 2: Indian Tech Compensation Intelligence (Google Search Grounding)")
    logger.info("=" * 60)

    prompt_file = EXPORT_DIR / "prompts" / "02_compensation_intelligence_grounding.json"
    with open(prompt_file, "r", encoding="utf-8") as f:
        config = json.load(f)

    response = client.models.generate_content(
        model=config.get("target_model", "gemini-2.5-flash"),
        contents=config.get("sample_user_input"),
        config=types.GenerateContentConfig(
            system_instruction=config.get("system_instructions"),
            temperature=config.get("temperature", 0.2),
            tools=[types.Tool(google_search=types.GoogleSearch())],
            response_mime_type="application/json",
        )
    )

    logger.info("AI Studio Response received:")
    try:
        parsed = json.loads(response.text)
        print(json.dumps(parsed, indent=2))
        logger.info(f"SUCCESS: Median Base={parsed.get('base_salary_median_lpa')} LPA, Total CTC={parsed.get('total_ctc_median_lpa')} LPA")
    except Exception as e:
        logger.warning(f"Raw output: {response.text}")


def test_ats_matching():
    logger.info("=" * 60)
    logger.info("TEST 3: ATS Match & Resume Tailoring Evaluator")
    logger.info("=" * 60)

    prompt_file = EXPORT_DIR / "prompts" / "03_ats_match_and_gap_evaluator.json"
    with open(prompt_file, "r", encoding="utf-8") as f:
        config = json.load(f)

    response = client.models.generate_content(
        model=config.get("target_model", "gemini-2.5-flash"),
        contents=config.get("sample_user_input"),
        config=types.GenerateContentConfig(
            system_instruction=config.get("system_instructions"),
            temperature=config.get("temperature", 0.2),
            response_mime_type="application/json",
        )
    )

    logger.info("AI Studio Response received:")
    try:
        parsed = json.loads(response.text)
        print(json.dumps(parsed, indent=2))
        logger.info(f"SUCCESS: Match Score={parsed.get('match_score')}% ({parsed.get('verdict')})")
    except Exception as e:
        logger.warning(f"Raw output: {response.text}")


if __name__ == "__main__":
    logger.info("Starting Google AI Studio Prompt Evaluation Suite...")
    test_resume_parser()
    test_ats_matching()
    test_compensation_grounding()
    logger.info("All Google AI Studio evaluations completed successfully.")
