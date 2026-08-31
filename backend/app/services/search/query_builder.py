"""
Search Query Builder
====================
Constructs optimized search query strings for:
  - Serper (LinkedIn, Naukri, Google Discovery)
  - Boolean search syntax (general)

All builders follow the Boolean operator standard supported by both
Google Search (via Serper) and direct portal search APIs.
"""

from pydantic import BaseModel, Field
from typing import List, Optional


class SearchCriteria(BaseModel):
    titles: List[str] = Field(
        default_factory=lambda: ["Software Engineer", "Backend Developer", "Senior Backend Engineer"]
    )
    required_skills: List[str] = Field(
        default_factory=lambda: ["Python", "FastAPI", "GCP"]
    )
    optional_skills: List[str] = Field(
        default_factory=lambda: ["Kubernetes", "PostgreSQL", "Docker", "Redis"]
    )
    excluded_keywords: List[str] = Field(
        default_factory=lambda: ["Intern", "Fresher", "Lead Manager", "QA Manual", "Sales", "Non-Tech"]
    )
    locations: List[str] = Field(
        default_factory=lambda: ["Bengaluru", "Pune", "Hyderabad", "Remote"]
    )
    min_exp_years: int = 3
    max_exp_years: int = 7
    min_ctc_lpa: Optional[float] = 20.0


# ---------------------------------------------------------------------------
# General Boolean Query (used by original workers / direct portal search)
# ---------------------------------------------------------------------------

def build_boolean_query(criteria: SearchCriteria) -> str:
    """
    Constructs an optimized Boolean search string.
    Example:
      ("Software Engineer" OR "Backend Developer") AND ("Python" OR "FastAPI" OR "GCP") NOT ("Intern" OR "Fresher")
    """
    title_group = (
        f"({' OR '.join([f'\"{t}\"' for t in criteria.titles])})" if criteria.titles else ""
    )
    must_have_group = (
        f"({' OR '.join([f'\"{s}\"' for s in criteria.required_skills])})"
        if criteria.required_skills
        else ""
    )
    exclude_group = (
        f"NOT ({' OR '.join([f'\"{e}\"' for e in criteria.excluded_keywords])})"
        if criteria.excluded_keywords
        else ""
    )
    parts = [p for p in [title_group, must_have_group, exclude_group] if p]
    return " AND ".join(parts)


# ---------------------------------------------------------------------------
# Serper-Optimised Query Builders
# ---------------------------------------------------------------------------

def build_serper_linkedin_query(criteria: SearchCriteria) -> str:
    """
    Constructs a Google Search query targeting LinkedIn Jobs for Indian tech roles.

    Strategy:
      - `site:in.linkedin.com/jobs` or `site:linkedin.com/jobs/view` anchors to live listings
      - Titles and top skills in quotes for high-precision matching
      - Experience bracket hint added as free text
      - Location OR Remote
      - Excluded terms after NOT operator (Serper supports basic Boolean)

    Example output:
      site:linkedin.com/jobs "Senior Backend Engineer" OR "Backend Developer" "Python" OR "FastAPI"
      "Bengaluru" OR "Pune" OR "Hyderabad" OR "Remote" "3-7 years" -intern -fresher
    """
    title_part = " OR ".join([f'"{t}"' for t in criteria.titles[:3]])
    skill_part = " OR ".join([f'"{s}"' for s in criteria.required_skills[:4]])
    loc_part = " OR ".join([f'"{loc}"' for loc in criteria.locations[:4]])
    exp_hint = f'"{criteria.min_exp_years}-{criteria.max_exp_years} years"'
    exclude_part = " ".join([f'-{e.lower()}' for e in criteria.excluded_keywords[:4]])

    return (
        f'site:linkedin.com/jobs ({title_part}) ({skill_part}) '
        f'({loc_part}) {exp_hint} {exclude_part}'
    ).strip()


def build_serper_naukri_query(criteria: SearchCriteria) -> str:
    """
    Constructs a Google Search query targeting Naukri.com listings.

    Naukri typically shows CTC and experience in snippets, making it possible
    to extract compensation signals from the search result snippets.
    """
    title_part = " OR ".join([f'"{t}"' for t in criteria.titles[:3]])
    skill_part = " OR ".join([f'"{s}"' for s in criteria.required_skills[:3]])
    loc_part = " OR ".join([f'"{loc}"' for loc in criteria.locations[:3]])
    exp_hint = f'"{criteria.min_exp_years} to {criteria.max_exp_years} years"'
    exclude_part = " ".join([f'-{e.lower()}' for e in criteria.excluded_keywords[:3]])

    return (
        f'site:naukri.com ({title_part}) ({skill_part}) '
        f'({loc_part}) {exp_hint} {exclude_part}'
    ).strip()


def build_serper_google_discovery_query(criteria: SearchCriteria) -> str:
    """
    Constructs a broad Google Search query for discovering unlisted jobs on:
    Greenhouse, Lever, Workday, SuccessFactors, and direct company career pages.

    This catches positions that aren't posted on major job boards yet.
    """
    title_part = " OR ".join([f'"{t}"' for t in criteria.titles[:2]])
    skill_part = " ".join(criteria.required_skills[:3])
    loc_part = " OR ".join([f'"{loc}"' for loc in criteria.locations[:3]])
    portals = 'site:boards.greenhouse.io OR site:lever.co OR site:jobs.lever.co OR site:myworkdayjobs.com OR site:careers.google.com'

    return (
        f'({portals}) ({title_part}) {skill_part} ({loc_part}) apply'
    ).strip()


def build_serper_hiring_manager_query(criteria: SearchCriteria) -> str:
    """
    Searches for LinkedIn posts from hiring managers actively posting
    about open roles — often before the job goes to a board.
    """
    title_part = " OR ".join([f'"{t}"' for t in criteria.titles[:2]])
    skill_part = " OR ".join(criteria.required_skills[:2])
    loc_part = " OR ".join(criteria.locations[:2])

    return (
        f'site:linkedin.com/posts ({title_part}) ({skill_part}) '
        f'({loc_part}) "hiring" OR "we are looking for" OR "join our team"'
    ).strip()


def build_naukri_search_params(criteria: SearchCriteria) -> dict:
    """Generates structured payload for Naukri key-skills and experience matrix search."""
    return {
        "keyword": " ".join(criteria.titles + criteria.required_skills),
        "experience_min": criteria.min_exp_years,
        "experience_max": criteria.max_exp_years,
        "locations": criteria.locations,
        "preferred_skills": criteria.optional_skills,
    }


def build_google_grounding_query(criteria: SearchCriteria) -> str:
    """Builds targeted Google Search Grounding query string for Indian tech portals."""
    titles_str = " OR ".join(criteria.titles[:2])
    locations_str = " OR ".join(criteria.locations[:3])
    skills_str = " ".join(criteria.required_skills[:3])
    return (
        f'site:linkedin.com/jobs OR site:naukri.com OR site:lever.co '
        f'OR site:greenhouse.io ({titles_str}) ({skills_str}) ({locations_str}) "apply"'
    )
