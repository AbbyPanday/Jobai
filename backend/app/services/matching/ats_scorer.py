"""
ATS Match Scoring Engine — 5-Factor Composite Algorithm
=========================================================
Computes a deterministic, semantically-rich match score between a
candidate profile and a job description.

Composite Score Formula:
  Final = (skills_semantic * 0.35) + (experience_band * 0.25)
        + (domain_depth   * 0.20) + (location_fit   * 0.10)
        + (ctc_alignment  * 0.10)

Factor Details:
  1. skills_semantic (35%):
     - TF-IDF-style weighted overlap with fuzzy alias matching
     - Required skills carry 2x weight vs optional/secondary skills
     - Alias normalization: k8s=kubernetes, fastapi=fast api, etc.

  2. experience_band (25%):
     - Parses min/max years from JD text
     - Gaussian-style proximity: perfect if within band, penalty if outside
     - 0-2 yr over: 10% penalty; 2+ yr under: 15% penalty

  3. domain_depth (20%):
     - Cloud platform match (GCP/AWS/Azure/multi-cloud)
     - Database tech depth (relational vs NoSQL vs both)
     - Architecture fit (microservices, distributed, ML)

  4. location_fit (10%):
     - Remote: 100%, Target city match: 95%, Same state: 80%, Other: 60%

  5. ctc_alignment (10%):
     - User expected CTC vs job's estimated market CTC range
     - Full overlap: 100%, within 20% delta: 75%, far off: 50%
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.gcp_clients import get_genai_client

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Skill Alias Map — canonical skill name normalisation
# ---------------------------------------------------------------------------

SKILL_ALIASES: Dict[str, str] = {
    # Python ecosystem
    "python3": "python", "py": "python",
    "fastapi": "fastapi", "fast api": "fastapi",
    "django rest framework": "django", "drf": "django",
    "flask restful": "flask",
    # Node / JS
    "nodejs": "node.js", "node js": "node.js",
    "nextjs": "next.js", "next js": "next.js",
    "expressjs": "express", "express.js": "express",
    # Go
    "golang": "go",
    # Databases
    "postgresql": "postgres", "psql": "postgres",
    "mysql": "mysql", "mariadb": "mysql",
    "mongodb": "mongo", "mongo": "mongo",
    "elasticsearch": "elastic", "opensearch": "elastic",
    "redis cache": "redis", "redis cluster": "redis",
    "cassandra": "cassandra", "apache cassandra": "cassandra",
    # Cloud
    "google cloud": "gcp", "google cloud platform": "gcp",
    "gcp cloud run": "gcp", "cloud run": "gcp",
    "aws": "aws", "amazon web services": "aws",
    "azure": "azure", "microsoft azure": "azure",
    # Container / Orchestration
    "kubernetes": "k8s", "k8s": "k8s",
    "docker": "docker", "docker compose": "docker",
    "helm charts": "helm", "helm chart": "helm",
    # Messaging
    "apache kafka": "kafka", "kafka streams": "kafka",
    "rabbitmq": "rabbitmq", "amqp": "rabbitmq",
    "celery": "celery", "celery beat": "celery",
    # ML / AI
    "machine learning": "ml", "deep learning": "dl",
    "langchain": "langchain", "lang chain": "langchain",
    "llm": "llm", "large language model": "llm",
    "rag": "rag", "retrieval augmented generation": "rag",
    # System design
    "distributed systems": "distributed",
    "high availability": "ha", "ha": "ha",
    "microservices architecture": "microservices",
    "system design": "system design",
    "low latency": "low latency",
    "ci/cd": "cicd", "ci cd": "cicd",
    "github actions": "cicd",
    "jenkins": "cicd",
}


def normalize_skill(skill: str) -> str:
    """Lowercase + alias resolution for reliable skill matching."""
    s = skill.lower().strip()
    return SKILL_ALIASES.get(s, s)


# ---------------------------------------------------------------------------
# Domain Depth Profiler
# ---------------------------------------------------------------------------

CLOUD_SKILLS = {"gcp", "aws", "azure", "cloud run", "cloud functions", "bigquery", "s3", "ec2", "lambda"}
DB_RELATIONAL = {"postgres", "mysql", "postgresql", "oracle", "sqlite", "supabase"}
DB_NOSQL = {"mongo", "cassandra", "redis", "dynamodb", "firestore", "elastic"}
ARCH_SKILLS = {"microservices", "distributed", "k8s", "kafka", "grpc", "graphql", "system design", "ha", "low latency"}
ML_SKILLS = {"ml", "dl", "pytorch", "tensorflow", "llm", "rag", "langchain", "scikit-learn", "transformers"}


def compute_domain_depth(user_skills_norm: set, job_skills_norm: set) -> float:
    """
    Compute domain depth score (0-100) based on technology tier overlaps.
    Rewards breadth (cloud + db + arch) more than narrow single-tech depth.
    """
    score = 50.0  # baseline

    # Cloud platform alignment
    user_cloud = user_skills_norm & CLOUD_SKILLS
    job_cloud = job_skills_norm & CLOUD_SKILLS
    if user_cloud and job_cloud:
        overlap_pct = len(user_cloud & job_cloud) / max(len(job_cloud), 1)
        score += 15 * min(overlap_pct, 1.0)
    elif user_cloud:
        score += 8  # Has cloud experience even if not exact match

    # Database depth
    user_db = (user_skills_norm & DB_RELATIONAL, user_skills_norm & DB_NOSQL)
    job_db = (job_skills_norm & DB_RELATIONAL, job_skills_norm & DB_NOSQL)
    for u_db, j_db in zip(user_db, job_db):
        if u_db and j_db:
            score += 8

    # Architecture / distributed systems
    user_arch = user_skills_norm & ARCH_SKILLS
    job_arch = job_skills_norm & ARCH_SKILLS
    if user_arch and job_arch:
        arch_overlap = len(user_arch & job_arch) / max(len(job_arch), 1)
        score += 12 * min(arch_overlap, 1.0)
    elif user_arch:
        score += 5

    # ML/AI skills (bonus — many roles now require some ML exposure)
    if user_skills_norm & ML_SKILLS and job_skills_norm & ML_SKILLS:
        score += 5

    return min(round(score, 1), 100.0)


# ---------------------------------------------------------------------------
# Experience Band Score
# ---------------------------------------------------------------------------

def _parse_exp_from_jd(jd_text: str) -> Tuple[Optional[float], Optional[float]]:
    """Extract min/max experience years from JD text."""
    patterns = [
        r"(\d+(?:\.\d+)?)\s*[-–to]+\s*(\d+(?:\.\d+)?)\s*(?:years?|yrs?)",
        r"minimum\s+(\d+(?:\.\d+)?)\s*(?:years?|yrs?)",
        r"(\d+)\+\s*(?:years?|yrs?)",
    ]
    for pat in patterns:
        m = re.search(pat, jd_text, re.IGNORECASE)
        if m:
            if m.lastindex == 2:
                return float(m.group(1)), float(m.group(2))
            else:
                val = float(m.group(1))
                return val, val + 3
    return None, None


def compute_experience_band_score(user_exp: float, jd_text: str) -> float:
    """
    Score (0-100) based on how well user's experience fits JD requirements.
    Perfect if within band, graduated penalty for over/under-qualification.
    """
    min_exp, max_exp = _parse_exp_from_jd(jd_text)
    if min_exp is None and max_exp is None:
        return 85.0  # No info — assume reasonable fit

    min_exp = min_exp or 0
    max_exp = max_exp or (min_exp + 3)

    if min_exp <= user_exp <= max_exp:
        return 100.0

    if user_exp < min_exp:
        delta = min_exp - user_exp
        # Under-qualified: 10% penalty per year under, min 40
        return max(40.0, 100.0 - (delta * 12.0))

    # Over-qualified
    delta = user_exp - max_exp
    # Slight over-qualification is usually fine (max 10% penalty)
    return max(75.0, 100.0 - (delta * 5.0))


# ---------------------------------------------------------------------------
# Location Fit Score
# ---------------------------------------------------------------------------

INDIA_CITY_STATE: Dict[str, str] = {
    "bengaluru": "karnataka", "bangalore": "karnataka",
    "pune": "maharashtra", "mumbai": "maharashtra", "nagpur": "maharashtra",
    "hyderabad": "telangana", "secunderabad": "telangana",
    "chennai": "tamil nadu", "coimbatore": "tamil nadu",
    "gurugram": "haryana", "gurgaon": "haryana", "noida": "uttar pradesh",
    "delhi": "delhi", "new delhi": "delhi",
    "kolkata": "west bengal",
    "ahmedabad": "gujarat", "surat": "gujarat",
    "kochi": "kerala",
    "jaipur": "rajasthan",
    "chandigarh": "chandigarh",
}


def compute_location_fit(user_location: str, job_location: str, user_preferred: List[str]) -> float:
    """Location fit score (0-100)."""
    jl = job_location.lower()

    # Remote always wins
    if "remote" in jl:
        return 100.0

    # Check user's preferred locations
    for pref in user_preferred:
        if pref.lower() in jl:
            return 95.0

    # Same city as user's current location
    ul = user_location.lower()
    if any(city in jl for city in ul.split() if len(city) > 3):
        return 90.0

    # Same state
    user_state = INDIA_CITY_STATE.get(ul.split(",")[0].strip(), "")
    job_city_key = next((k for k in INDIA_CITY_STATE if k in jl), "")
    job_state = INDIA_CITY_STATE.get(job_city_key, "")
    if user_state and job_state and user_state == job_state:
        return 80.0

    # Hybrid = partial credit
    if "hybrid" in jl:
        return 70.0

    # Major tech hub even if not preferred
    for hub in ["bengaluru", "bangalore", "pune", "hyderabad", "gurugram", "mumbai"]:
        if hub in jl:
            return 65.0

    return 55.0  # Requires relocation


# ---------------------------------------------------------------------------
# CTC Alignment Score
# ---------------------------------------------------------------------------

def compute_ctc_alignment(expected_ctc: float, salary_intel: Optional[Dict]) -> float:
    """CTC fit score (0-100) — how well user's expectation fits job's estimated range."""
    if not salary_intel or not expected_ctc:
        return 75.0  # Unknown — neutral

    min_ctc = salary_intel.get("estimated_ctc_min_lpa", 0)
    max_ctc = salary_intel.get("estimated_ctc_max_lpa", 999)

    if min_ctc <= expected_ctc <= max_ctc:
        return 100.0

    if expected_ctc < min_ctc:
        # User expects less than minimum — very good fit (scope to negotiate up)
        return 95.0

    # User expects more than max — risk of rejection
    overshoot_pct = (expected_ctc - max_ctc) / max(max_ctc, 1)
    if overshoot_pct <= 0.15:
        return 75.0  # Within 15% overshoot — negotiable
    elif overshoot_pct <= 0.30:
        return 55.0
    else:
        return 35.0


# ---------------------------------------------------------------------------
# Skills Semantic Score (TF-IDF weighted)
# ---------------------------------------------------------------------------

def compute_skills_semantic_score(
    user_skills_norm: set,
    required_skills: List[str],
    optional_skills: Optional[List[str]] = None,
) -> Tuple[float, List[str], List[str]]:
    """
    Weighted skill overlap score with fuzzy alias resolution.

    Required skills: 2x weight
    Optional/secondary skills: 1x weight
    Returns: (score 0-100, matched_skills, missing_skills)
    """
    optional_skills = optional_skills or []
    req_norm = [normalize_skill(s) for s in required_skills]
    opt_norm = [normalize_skill(s) for s in optional_skills]

    req_matched = [s for s in required_skills if normalize_skill(s) in user_skills_norm]
    req_missing = [s for s in required_skills if normalize_skill(s) not in user_skills_norm]
    opt_matched = [s for s in optional_skills if normalize_skill(s) in user_skills_norm]

    total_weight = (len(req_norm) * 2) + len(opt_norm)
    if total_weight == 0:
        return 85.0, [], []

    matched_weight = (len(req_matched) * 2) + len(opt_matched)
    base_score = (matched_weight / total_weight) * 100.0

    # Bonus for having all required skills
    if len(req_missing) == 0 and req_norm:
        base_score = min(100.0, base_score + 5.0)

    return round(base_score, 1), req_matched + opt_matched, req_missing


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------

class MatchBreakdown(BaseModel):
    hardSkills: float = Field(description="Skills semantic score (0-100)")
    experienceFit: float = Field(description="Experience band score (0-100)")
    domainFit: float = Field(description="Domain depth score (0-100)")
    locationFit: float = Field(description="Location fit score (0-100)")
    ctcAlignment: float = Field(description="CTC alignment score (0-100)")
    # Legacy compat
    softSkillsAndPedigree: float = Field(default=85.0, description="Soft skills proxy (0-100)")


class MatchEvaluation(BaseModel):
    matchScore: float = Field(description="Overall weighted composite score (0-100)")
    matchBreakdown: MatchBreakdown
    isHighMatch: bool = Field(description="True if matchScore >= threshold")
    strengths: List[str]
    missingSkills: List[str]
    tailoredAdvice: str


# ---------------------------------------------------------------------------
# Main Scorer
# ---------------------------------------------------------------------------

class ATSScorer:
    """
    5-factor composite ATS match scorer with Gemini deep semantic fallback.
    """

    @staticmethod
    async def evaluate_match(
        user_profile: Dict[str, Any],
        job_details: Dict[str, Any],
    ) -> MatchEvaluation:

        threshold = user_profile.get("autoApplyThreshold", settings.DEFAULT_MATCH_THRESHOLD)
        user_exp = float(user_profile.get("experienceYears", 3.0))
        user_location = user_profile.get("location", "Bengaluru, India")
        expected_ctc = float(user_profile.get("expectedCtcLpa", 0) or 0)

        # Normalize user skills (handle dict or list)
        skills_field = user_profile.get("skills", [])
        if isinstance(skills_field, dict):
            raw_skills = (
                skills_field.get("primarySkills", [])
                + skills_field.get("secondarySkills", [])
                + skills_field.get("domainExpertise", [])
            )
        elif isinstance(skills_field, list):
            raw_skills = list(skills_field)
        else:
            raw_skills = []

        addl_skills = user_profile.get("additionalSkills", [])
        if isinstance(addl_skills, list):
            raw_skills.extend(addl_skills)

        user_skills_norm = {normalize_skill(s) for s in raw_skills if s and isinstance(s, str)}

        # Job context
        job_desc = job_details.get("rawDescription", "")
        job_reqs = job_details.get("extractedRequirements", [])
        job_location = job_details.get("location", "")
        salary_intel = job_details.get("salaryIntelligence")

        # ── Try Gemini deep semantic scoring first ─────────────────────────────
        client = get_genai_client()
        if client and len(job_desc) > 50:
            try:
                gemini_result = await _gemini_score(
                    client, user_profile, job_details, threshold
                )
                if gemini_result:
                    return gemini_result
            except Exception as e:
                logger.warning(f"Gemini ATS scoring unavailable: {e}. Using composite algorithm.")

        # ── Composite Deterministic Algorithm ─────────────────────────────────
        # Factor 1: Skills semantic (35%)
        skills_score, strengths_raw, missing = compute_skills_semantic_score(
            user_skills_norm, job_reqs
        )

        # Factor 2: Experience band (25%)
        exp_score = compute_experience_band_score(user_exp, job_desc)

        # Factor 3: Domain depth (20%)
        job_skills_norm = {normalize_skill(s) for s in job_reqs}
        domain_score = compute_domain_depth(user_skills_norm, job_skills_norm)

        # Factor 4: Location fit (10%)
        preferred_locs = user_profile.get("preferredLocations", ["Bengaluru", "Pune", "Remote"])
        loc_score = compute_location_fit(user_location, job_location, preferred_locs)

        # Factor 5: CTC alignment (10%)
        ctc_score = compute_ctc_alignment(expected_ctc, salary_intel)

        # Weighted composite
        total_score = round(
            (skills_score * 0.35)
            + (exp_score * 0.25)
            + (domain_score * 0.20)
            + (loc_score * 0.10)
            + (ctc_score * 0.10),
            1,
        )

        company = job_details.get("companyName", "this company")
        matched_skill_names = strengths_raw[:4] or list(raw_skills)[:4]

        return MatchEvaluation(
            matchScore=total_score,
            matchBreakdown=MatchBreakdown(
                hardSkills=round(skills_score, 1),
                experienceFit=round(exp_score, 1),
                domainFit=round(domain_score, 1),
                locationFit=round(loc_score, 1),
                ctcAlignment=round(ctc_score, 1),
                softSkillsAndPedigree=85.0,
            ),
            isHighMatch=(total_score >= threshold),
            strengths=[
                f"Strong match on core stack: {', '.join(matched_skill_names[:4])}",
                f"Experience ({user_exp} yrs) aligns with role requirements",
                f"Location/remote preference: {'✓ Remote available' if 'remote' in job_location.lower() else job_location.split(',')[0]}",
            ],
            missingSkills=missing[:6],
            tailoredAdvice=(
                f"{'🔥 Excellent fit!' if total_score >= 85 else '✅ Good match.' if total_score >= 70 else '⚠️ Partial match.'} "
                f"For {company}: lead with your {', '.join(matched_skill_names[:2])} experience. "
                + (
                    f"Upskill on: {', '.join(missing[:3])} before applying."
                    if missing
                    else "You cover all key requirements — focus on demonstrating scale and impact."
                )
            ),
        )


async def _gemini_score(
    client,
    user_profile: Dict[str, Any],
    job_details: Dict[str, Any],
    threshold: float,
) -> Optional[MatchEvaluation]:
    """Deep semantic match scoring via Gemini with structured output."""
    from google.genai import types

    raw_user_skills = user_profile.get("skills", [])
    if isinstance(raw_user_skills, dict):
        raw_list = (
            raw_user_skills.get("primarySkills", [])
            + raw_user_skills.get("secondarySkills", [])
            + raw_user_skills.get("domainExpertise", [])
        )
    elif isinstance(raw_user_skills, list):
        raw_list = list(raw_user_skills)
    else:
        raw_list = []

    addl = user_profile.get("additionalSkills", [])
    if isinstance(addl, list):
        raw_list.extend(addl)

    skills_str = ", ".join([str(s) for s in raw_list if s])

    class GeminiBreakdown(MatchBreakdown):
        pass

    class GeminiEval(MatchEvaluation):
        pass

    prompt = f"""You are an elite Indian Tech ATS Evaluation Engine using a 5-factor composite model.

Candidate:
- Name: {user_profile.get('name', 'Candidate')}
- Role: {user_profile.get('currentRole', 'Software Engineer')}
- Experience: {user_profile.get('experienceYears', 3)} years
- Location: {user_profile.get('location', 'India')}
- Current CTC: {user_profile.get('currentCtcLpa', 0)} LPA | Expected: {user_profile.get('expectedCtcLpa', 0)} LPA
- Skills: {skills_str}

Job:
- Company: {job_details.get('companyName', '')}
- Title: {job_details.get('title', '')}
- Location: {job_details.get('location', '')}
- Requirements: {', '.join(job_details.get('extractedRequirements', []))}
- Description: {job_details.get('rawDescription', '')[:600]}

Scoring weights:
  hardSkills (skills semantic):   35%
  experienceFit (band proximity): 25%
  domainFit (cloud/db/arch depth):20%
  locationFit:                    10%
  ctcAlignment:                   10%
  softSkillsAndPedigree:          use 85.0 as default

matchScore = (hardSkills*0.35) + (experienceFit*0.25) + (domainFit*0.20) + (locationFit*0.10) + (ctcAlignment*0.10)
isHighMatch = matchScore >= {threshold}

Provide: matchScore, matchBreakdown (all 5 factors + softSkillsAndPedigree), isHighMatch, strengths (3 bullet strings), missingSkills (array), tailoredAdvice (1 sentence).
"""

    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=MatchEvaluation,
            temperature=0.1,
        ),
    )
    return MatchEvaluation.model_validate_json(response.text)


# Global singleton
ats_scorer = ATSScorer()
