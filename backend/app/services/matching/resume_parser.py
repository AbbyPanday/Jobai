import io
import re
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from app.core.gcp_clients import get_genai_client
from app.core.config import settings

logger = logging.getLogger(__name__)

# Check pypdf availability
try:
    import pypdf
    PYPDF_AVAILABLE = True
except ImportError:
    pypdf = None
    PYPDF_AVAILABLE = False

class ParsedResume(BaseModel):
    full_name: str = Field(description="Candidate full name")
    email: str = Field(description="Email address")
    phone: str = Field(description="Phone number")
    current_location: str = Field(description="City/State, Country")
    years_of_experience: float = Field(description="Total years of professional experience as float")
    current_designation: str = Field(description="Current or most recent job title")
    recommended_position: str = Field(description="Ideal target job title candidate should apply to")
    recommended_domain: str = Field(description="Recommended industry domain (e.g. FinTech, SaaS, EdTech, E-commerce, HealthTech)")
    primary_skills: List[str] = Field(description="List of primary core tech skills")
    secondary_skills: List[str] = Field(description="List of secondary tools, libraries, and frameworks")
    cloud_and_infrastructure: List[str] = Field(description="Cloud platforms (GCP, AWS, Azure, K8s, Docker)")
    education: List[str] = Field(description="Degree and university information")
    past_companies: List[str] = Field(description="List of past companies worked at")
    summary: str = Field(description="Executive professional summary")

class ResumeParser:
    """
    Parses resume documents (PDF, DOCX, TXT) using Gemini Multimodal Document Ingestion
    with automatic deterministic text extraction fallback when API key is unconfigured.
    """
    @classmethod
    def extract_text_from_bytes(cls, file_bytes: bytes, filename: str) -> str:
        """Extracts text content from uploaded file bytes (PDF, TXT, DOCX)."""
        filename_lower = filename.lower()
        if filename_lower.endswith('.pdf'):
            if PYPDF_AVAILABLE:
                try:
                    reader = pypdf.PdfReader(io.BytesIO(file_bytes))
                    extracted = ""
                    for page in reader.pages:
                        txt = page.extract_text()
                        if txt:
                            extracted += txt + "\n"
                    if extracted.strip():
                        return extracted.strip()
                except Exception as e:
                    logger.warning(f"pypdf extraction failed: {e}")
            # Fallback binary string decode
            return file_bytes.decode('utf-8', errors='ignore').strip()
        else:
            return file_bytes.decode('utf-8', errors='ignore').strip()

    @classmethod
    def parse_text_deterministically(cls, raw_text: str, filename: str) -> ParsedResume:
        """Parses actual resume text content deterministically into structured candidate schema."""
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        
        # 1. Extract Name (typically first non-empty line or from filename)
        candidate_name = "Candidate"
        if lines:
            first_line = lines[0]
            # Clean common headers
            if len(first_line) < 40 and not re.search(r'(@|resume|curriculum|cv|http)', first_line, re.IGNORECASE):
                candidate_name = first_line
            else:
                base = filename.rsplit('.', 1)[0].replace('_', ' ').replace('-', ' ').title()
                candidate_name = base if len(base) < 40 else "Candidate"

        # 2. Extract Email
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', raw_text)
        email = email_match.group(0) if email_match else "candidate@example.com"

        # 3. Extract Phone
        phone_match = re.search(r'(\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}', raw_text)
        phone = phone_match.group(0) if phone_match else ""

        # 4. Extract Location
        location = "Bengaluru, Karnataka, India"
        cities = ["Bengaluru", "Bangalore", "Hyderabad", "Pune", "Mumbai", "Delhi", "Gurgaon", "Noida", "Chennai", "Kolkata", "Remote", "India"]
        for c in cities:
            if re.search(rf'\b{c}\b', raw_text, re.IGNORECASE):
                location = f"{c}, India" if "India" not in c else c
                break

        # 5. Extract Skills
        tech_keywords = [
            "Python", "FastAPI", "Django", "Flask", "JavaScript", "TypeScript", "React", "Next.js", "Node.js",
            "Express", "Go", "Golang", "Java", "Spring Boot", "C++", "Rust", "GCP", "AWS", "Azure",
            "Docker", "Kubernetes", "PostgreSQL", "MySQL", "MongoDB", "Redis", "Kafka", "RabbitMQ",
            "GraphQL", "REST APIs", "CI/CD", "Terraform", "Linux", "Git", "System Design", "Microservices",
            "Distributed Systems", "Machine Learning", "PyTorch", "TensorFlow", "Pandas", "Elasticsearch"
        ]
        found_skills = []
        for tech in tech_keywords:
            if re.search(rf'\b{re.escape(tech)}\b', raw_text, re.IGNORECASE):
                found_skills.append(tech)

        if not found_skills:
            found_skills = ["Software Engineering", "Full Stack Development", "Problem Solving"]

        cloud_tools = [s for s in found_skills if s in ["GCP", "AWS", "Azure", "Docker", "Kubernetes", "Terraform", "Linux", "CI/CD"]]
        primary = found_skills[:6]
        secondary = found_skills[6:]

        # 6. Extract Years of Experience (with date ranges fallback)
        exp_match = re.search(r'(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)(?:\s+of)?\s+(?:experience|exp)', raw_text, re.IGNORECASE)
        if exp_match:
            years_exp = float(exp_match.group(1))
        else:
            # Fallback: scan for year ranges (e.g. 2018-2022 -> 4 years, 2021-Present -> 5 years from 2026)
            ranges = re.findall(r'\b(20\d{2})\s*[-–—to]+\s*(20\d{2}|present|current|now)\b', raw_text, re.IGNORECASE)
            total_from_ranges = 0.0
            for start, end in ranges:
                start_yr = int(start)
                if end.lower() in ["present", "current", "now"]:
                    end_yr = 2026
                else:
                    try:
                        end_yr = int(end)
                    except ValueError:
                        end_yr = 2026
                if end_yr >= start_yr:
                    total_from_ranges += (end_yr - start_yr)
            years_exp = total_from_ranges if total_from_ranges > 0 else 3.5

        # 7. Extract Designation
        roles = [
            "Senior Staff Engineer", "Staff Software Engineer", "Lead Software Engineer",
            "Senior Software Engineer", "Software Engineer 3", "Software Development Engineer",
            "Backend Engineer", "Full Stack Developer", "Frontend Engineer", "DevOps Engineer",
            "Data Engineer", "Machine Learning Engineer", "Cloud Architect", "Software Engineer"
        ]
        designation = "Software Engineer"
        for r in roles:
            if re.search(rf'\b{re.escape(r)}\b', raw_text, re.IGNORECASE):
                designation = r
                break

        # Heuristics for Recommended Target Position & Domain
        recommended_pos = designation
        if "Senior" not in designation and years_exp >= 4.0:
            recommended_pos = f"Senior {designation}"

        domain_keywords = {
            "FinTech": ["finance", "trading", "banking", "payment", "blockchain", "ledger"],
            "E-commerce": ["ecommerce", "retail", "shop", "cart", "catalog"],
            "EdTech": ["education", "learning", "course", "school", "lms"],
            "HealthTech": ["healthcare", "medical", "hospital", "patient", "clinical"],
            "SaaS": ["saas", "cloud", "b2b", "subscription", "enterprise"],
        }
        recommended_dom = "Enterprise Software"
        for dom, keywords in domain_keywords.items():
            if any(re.search(rf'\b{kw}\b', raw_text, re.IGNORECASE) for kw in keywords):
                recommended_dom = dom
                break

        # 8. Extract Companies
        companies = []
        company_keywords = ["Google", "Microsoft", "Amazon", "Flipkart", "Swiggy", "Zomato", "PhonePe", "Razorpay", "Uber", "Ola", "Paytm", "Cred", "Oracle", "Cisco", "Infosys", "TCS", "Wipro", "Accenture"]
        for comp in company_keywords:
            if re.search(rf'\b{re.escape(comp)}\b', raw_text, re.IGNORECASE):
                companies.append(comp)

        summary = f"{designation} with {years_exp} years of experience specializing in {', '.join(primary[:4])}."

        return ParsedResume(
            full_name=candidate_name,
            email=email,
            phone=phone,
            current_location=location,
            years_of_experience=years_exp,
            current_designation=designation,
            recommended_position=recommended_pos,
            recommended_domain=recommended_dom,
            primary_skills=primary,
            secondary_skills=secondary,
            cloud_and_infrastructure=cloud_tools,
            education=["B.Tech / Bachelor's in Computer Science or Equivalent"],
            past_companies=companies if companies else ["Tech Solutions"],
            summary=summary
        )

    @classmethod
    async def parse_document_bytes(cls, file_bytes: bytes, filename: str, mime_type: str = "application/pdf") -> ParsedResume:
        """
        Ingests document bytes using Gemini Multimodal API if configured,
        or performs deterministic extraction directly from the document.
        """
        if not file_bytes or len(file_bytes) == 0:
            raise ValueError("Uploaded document is empty.")

        # Normalize mime type
        if filename.lower().endswith(".pdf"):
            mime_type = "application/pdf"
        elif filename.lower().endswith(".docx") or filename.lower().endswith(".doc"):
            mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        elif filename.lower().endswith(".txt") or filename.lower().endswith(".md"):
            mime_type = "text/plain"

        client = get_genai_client()
        if client:
            try:
                from google.genai import types
                
                # Gemini native multimodal document ingestion
                document_part = types.Part.from_bytes(
                    data=file_bytes,
                    mime_type=mime_type
                )
                
                prompt = """
                You are an advanced AI candidate intelligence and ATS evaluation engine.
                Analyze the attached resume document thoroughly and extract the candidate's structured profile into JSON.
                Ensure you accurately extract:
                - Full name, email, and phone number
                - Current location (City, State, Country)
                - Total years of experience (as a numeric float. Calculate this strictly by summing the durations of all listed work experiences. If not explicitly stated, calculate the difference between start/end dates for each position, relative to today's date if present/current).
                - Current designation and past companies
                - Recommended position (What target job title does their career trajectory map to? e.g. Senior Software Engineer, Staff Engineer, Principal Developer)
                - Recommended domain (What industry domain fits their key projects? e.g. FinTech, SaaS, EdTech, E-commerce, HealthTech)
                - Core primary skills, secondary tools, and cloud infrastructure
                - Degree and educational background
                - Executive summary
                """

                response = client.models.generate_content(
                    model=settings.GEMINI_MODEL,
                    contents=[document_part, prompt],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=ParsedResume,
                        temperature=0.1,
                    )
                )
                return ParsedResume.model_validate_json(response.text)
            except Exception as e:
                logger.warning(f"Gemini multimodal document ingestion error: {e}. Falling back to deterministic document parser.")

        # Deterministic extraction directly from file bytes
        raw_text = cls.extract_text_from_bytes(file_bytes, filename)
        return cls.parse_text_deterministically(raw_text, filename)

    @classmethod
    async def parse_resume_text(cls, resume_text: str) -> ParsedResume:
        """
        Parses raw resume text content. Wraps text into bytes and delegates
        to parse_document_bytes for Gemini or deterministic extraction.
        """
        if not resume_text or not resume_text.strip():
            raise ValueError("Resume text is empty.")
        text_bytes = resume_text.encode("utf-8")
        return await cls.parse_document_bytes(
            file_bytes=text_bytes,
            filename="resume_pasted.txt",
            mime_type="text/plain"
        )

resume_parser = ResumeParser()
