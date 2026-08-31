import logging
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

class FormFieldMapper:
    """
    Intelligently maps candidate persona fields to DOM / ATS form elements
    (Workday, Greenhouse, Lever, Direct portals) and identifies unknown/missing inputs.
    """
    
    @staticmethod
    def map_candidate_fields(user_profile: Dict[str, Any], custom_answers: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        answers = custom_answers or {}
        
        return {
            "first_name": user_profile.get("name", "").split(" ")[0],
            "last_name": " ".join(user_profile.get("name", "").split(" ")[1:]) or "Candidate",
            "full_name": user_profile.get("name", ""),
            "email": user_profile.get("email", ""),
            "phone": user_profile.get("phone", ""),
            "location": user_profile.get("location", "Bengaluru, India"),
            "current_role": user_profile.get("currentRole", "Software Engineer"),
            "total_experience_years": str(user_profile.get("experienceYears", 4.5)),
            "current_ctc_lpa": str(user_profile.get("currentCtcLpa", 18.0)),
            "expected_ctc_lpa": str(answers.get("expected_ctc", user_profile.get("expectedCtcLpa", 28.0))),
            "notice_period_days": str(answers.get("notice_period", user_profile.get("noticePeriodDays", 30))),
            "notice_period_text": f"{answers.get('notice_period', user_profile.get('noticePeriodDays', 30))} Days (Negotiable / Official)",
            "primary_skills": ", ".join(user_profile.get("skills", [])),
            "linkedin_url": "https://linkedin.com/in/" + user_profile.get("name", "candidate").lower().replace(" ", ""),
            "github_url": "https://github.com/" + user_profile.get("name", "candidate").lower().replace(" ", ""),
            "authorized_to_work_in_india": "Yes",
            "require_sponsorship": "No",
            "preferred_work_mode": "Hybrid / Remote",
            **answers
        }

    @staticmethod
    def identify_missing_questions(
        portal_fields: List[str],
        mapped_data: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """
        Checks if the portal requires custom questions not answered in candidate's master persona.
        """
        missing = []
        for field in portal_fields:
            normalized = field.lower().strip()
            if "notice" in normalized and not mapped_data.get("notice_period_days"):
                missing.append({
                    "questionKey": "notice_period",
                    "label": "What is your official notice period in days?",
                    "type": "number",
                    "placeholder": "e.g. 30"
                })
            elif "expected ctc" in normalized and not mapped_data.get("expected_ctc_lpa"):
                missing.append({
                    "questionKey": "expected_ctc",
                    "label": "What is your Expected CTC in LPA (Lakhs per Annum)?",
                    "type": "number",
                    "placeholder": "e.g. 28"
                })
        return missing

form_mapper = FormFieldMapper()
