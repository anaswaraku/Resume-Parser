"""
Job Description Matching (POST /match-job).

Primary path (use_llm=True):
  - LLM extracts structured skills from the JD (normalised, abbreviations expanded)
  - Resume skills come from the hybrid parser
  - Match is done with token-overlap fuzzy comparison (handles single-word vs phrase)

Fallback (use_llm=False):
  - Metadata header stripped from JD before keyword extraction
  - Keyword extraction on remaining body text only
  - Same fuzzy matching applied
"""

from __future__ import annotations
import re
from typing import List, Set, Optional
from pydantic import BaseModel
from utils.words import _SYNONYMS, _STOP, _MULTI_WORD_SKILLS


# ── Response model ─────────────────────────────────────────────────────────────

class JobMatchResult(BaseModel):
    """Final Output"""
    matched_skills: List[str]
    missing_skills: List[str]
    extra_skills:   List[str]       # on resume but not required by JD
    score:          float           # 0.0 – 1.0
    score_pct:      float           # 0.0 – 100.0
    extraction_method: str          # "llm" | "keyword"


# ── JD metadata stripping ──────────────────────────────────────────────────────

# Additional noise tokens that slip past _STOP (location names, company
# metadata, date formats, boilerplate fragments specific to JD headers).
_JD_NOISE: Set[str] = {
    # Location / company boilerplate
    "india", "pune", "maharashtra", "mumbai", "bangalore", "bengaluru",
    "hyderabad", "chennai", "delhi", "noida", "gurugram", "gurgaon",
    "kochi", "thrissur", "kerala", "karnataka", "tamil",
    "siemens", "infosys", "tcs", "wipro", "accenture", "cognizant",
    "private", "limited", "pvt", "ltd", "inc", "corp", "llc",
    # JD structural keywords
    "posted", "since", "organization", "field", "employment", "type",
    "mode", "hybrid", "onsite", "office", "site", "full", "time",
    "part", "contract", "permanent", "temporary", "fresher",
    # Filler adjectives / adverbs common in JDs
    "accelerated", "across", "advantage", "agentic", "applying",
    "approach", "architecture", "broadly", "cars", "ships",
    "manufacture", "manufactured", "many", "skyscrapers",
    # Date-like tokens
    "jan", "feb", "mar", "apr", "may", "jun", "jul", "aug",
    "sep", "oct", "nov", "dec",
}

_JD_METADATA_RE = re.compile(
    r'^.*?(?=position\s+overview|about\s+the\s+role|responsibilities|'
    r'job\s+description\b|overview\b|about\s+us|what\s+you|'
    r'we\s+are\s+looking|requirements\b|qualifications\b)',
    re.I | re.DOTALL,
)

_DATE_TOKEN_RE = re.compile(
    r'^\d{2}-[a-z]{3}-\d{4}$'   # jun-2026
    r'|^\d{4}$'                  # 2024
    r'|^\d{1,2}/\d{4}$',        # 06/2026
    re.I,
)


def _strip_jd_metadata(jd_text: str) -> str:
    """
    Remove the job-posting header block (Job ID, Posted since, Location, etc.)
    so keyword extraction operates only on the actual job description body.
    """
    m = _JD_METADATA_RE.match(jd_text)
    if m and m.end() < len(jd_text):
        return jd_text[m.end():]
    return jd_text


# ── Normalisation ──────────────────────────────────────────────────────────────

def _normalise(skill: str) -> str:
    """Lowercase, strip punctuation noise, apply synonym map."""
    s = re.sub(r'\s*\([^)]*\)', '', skill).strip()
    s_lower = s.lower().strip(" .,;:-")
    return _SYNONYMS.get(s_lower, s_lower)


def _normalise_set(skills: List[str]) -> Set[str]:
    """Normalises a list of skills to a set of canonical forms."""
    return {_normalise(s) for s in skills if s and s.strip()}


# ── Keyword extraction (keyword-fallback path) ─────────────────────────────────

def _is_noise_token(tok: str) -> bool:
    """True for tokens that are definitely not skills."""
    t = tok.strip().lower()
    if not t or len(t) <= 2:
        return True
    if t in _STOP or t in _JD_NOISE:
        return True
    if _DATE_TOKEN_RE.match(t):
        return True
    return False


def _extract_keywords(text: str) -> Set[str]:
    # Strip emails and URLs before tokenisation so they don't fragment into
    # pseudo-tokens like "gmail.com", "arjun", "linkedin"
    text = re.sub(r'[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}', ' ', text)
    text = re.sub(r'https?://\S+|www\.\S+', ' ', text)
    text = re.sub(r'\b[A-Za-z0-9.\-]+\.(com|in|org|io|net|ai|co)\b', ' ', text)

    text_lower = text.lower()
    found: Set[str] = set()

    # Multi-word skills first (longest-match first, already sorted by len desc)
    for phrase in _MULTI_WORD_SKILLS:
        if phrase in text_lower:
            found.add(phrase)
            text_lower = text_lower.replace(phrase, " ")

    for tok in re.findall(r"[a-z][a-z0-9#\+\.\-\/]*", text_lower):
        cleaned = tok.strip(".,;")
        if not _is_noise_token(cleaned):
            found.add(cleaned)

    return found


# ── Fuzzy token-overlap matching ───────────────────────────────────────────────

_MATCH_STOP: Set[str] = {
    "and", "or", "with", "for", "the", "a", "an", "of", "in",
    "to", "using", "based", "driven", "oriented",
}


def _skill_tokens(s: str) -> Set[str]:
    """
    Break a skill phrase into meaningful tokens.
    "Python development" → {"python", "development"}
    "SQL databases"      → {"sql", "databases"}
    """
    s = s.lower().strip()
    s = re.sub(r"[^\w\s\-]", "", s)
    tokens = re.findall(r'\b[a-z][a-z0-9\-]{0,}\b', s)
    return {t for t in tokens if t not in _MATCH_STOP and len(t) > 1}


def _skills_match(resume_skill: str, jd_skill: str, threshold: float = 0.6) -> bool:
    """
    True if resume_skill and jd_skill refer to the same skill.

    Uses token overlap so single-word resume skills match multi-word JD phrases:
      "python"         vs "Python development"  → overlap=1, smaller=1 → 1.0 ✅
      "sql"            vs "SQL databases"        → overlap=1, smaller=1 → 1.0 ✅
      "machine learning" vs "Machine Learning"  → overlap=2, smaller=2 → 1.0 ✅
      "git"            vs "Git workflows"        → overlap=1, smaller=1 → 1.0 ✅
    """
    # Fast path: exact normalised match
    if _normalise(resume_skill) == _normalise(jd_skill):
        return True

    r_tokens = _skill_tokens(resume_skill)
    j_tokens = _skill_tokens(jd_skill)
    if not r_tokens or not j_tokens:
        return False

    overlap = len(r_tokens & j_tokens)
    smaller = min(len(r_tokens), len(j_tokens))
    return (overlap / smaller) >= threshold


# ── Core match computation ─────────────────────────────────────────────────────

def _compute_match(
    resume_skills: List[str],
    jd_skills:     List[str],
    method:        str,
) -> JobMatchResult:
    """
    Fuzzy token-overlap matching between resume skills and JD skills.
    Returns matched/missing/extra lists and a score.
    """
    if not jd_skills:
        return JobMatchResult(
            matched_skills=[],
            missing_skills=[],
            extra_skills=sorted(resume_skills),
            score=0.0,
            score_pct=0.0,
            extraction_method=method,
        )

    matched_jd:  List[str] = []
    missing_jd:  List[str] = []

    for jd_skill in jd_skills:
        if any(_skills_match(rs, jd_skill) for rs in resume_skills):
            matched_jd.append(jd_skill)
        else:
            missing_jd.append(jd_skill)

    # Extra = resume skills not covered by any matched JD skill
    matched_jd_set = set(matched_jd)
    extra_resume: List[str] = [
        rs for rs in resume_skills
        if not any(_skills_match(rs, js) for js in matched_jd_set)
    ]

    score = len(matched_jd) / len(jd_skills)

    return JobMatchResult(
        matched_skills=sorted(matched_jd),
        missing_skills=sorted(missing_jd),
        extra_skills=sorted(extra_resume),
        score=round(score, 4),
        score_pct=round(score * 100, 1),
        extraction_method=method,
    )


# ── Public API ─────────────────────────────────────────────────────────────────

def match_job(
    resume_skills: List[str],
    resume_text:   str,
    jd_text:       str,
    jd_skills_llm: Optional[List[str]] = None,   # pre-extracted by LLM
) -> JobMatchResult:
    """
    Compare resume against a job description.

    LLM path  (jd_skills_llm provided):
      - Uses LLM-extracted, structured JD skills.
      - Resume skills augmented by keyword extraction on full resume text.
      - Fuzzy token-overlap matching handles single-word vs phrase granularity.

    Keyword fallback (jd_skills_llm is None):
      - JD metadata header stripped before extraction to avoid location/date noise.
      - Same fuzzy matching applied.
    """
    if jd_skills_llm is not None:
        # Augment parsed resume skills with keyword extraction on full resume text
        resume_kw = _extract_keywords(" ".join(resume_skills) + " " + resume_text)
        # Combine: parsed skills take display priority, keywords fill gaps
        all_resume = list({s.lower(): s for s in list(resume_skills) + sorted(resume_kw)}.values())

        return _compute_match(
            resume_skills=all_resume,
            jd_skills=jd_skills_llm,
            method="llm",
        )
    else:
        # Strip JD header before keyword extraction
        jd_body = _strip_jd_metadata(jd_text)
        resume_kw = _extract_keywords(" ".join(resume_skills) + " " + resume_text)
        jd_kw     = _extract_keywords(jd_body)

        all_resume = list({s.lower(): s for s in list(resume_skills) + sorted(resume_kw)}.values())

        return _compute_match(
            resume_skills=all_resume,
            jd_skills=sorted(jd_kw),
            method="keyword",
        )
