"""
Job Description Matching (POST /match-job).

Primary path (use_llm=True):
  - LLM extracts structured skills from the JD (normalised, abbreviations expanded)
  - Resume skills come from the hybrid parser
  - Match is done on normalised skill strings with synonym expansion

Fallback (use_llm=False):
  - Keyword extraction from raw JD text
  - Resume keywords from raw resume text + parsed skills
"""

from __future__ import annotations
import re
from typing import List, Set, Optional
from pydantic import BaseModel
from utils.words import _SYNONYMS, _STOP,_MULTI_WORD_SKILLS


#Response model 

class JobMatchResult(BaseModel):
    """Final Output"""
    matched_skills: List[str]
    missing_skills: List[str]
    extra_skills:   List[str]       # on resume but not required by JD
    score:          float           # 0.0 – 1.0
    score_pct:      float           # 0.0 – 100.0
    extraction_method: str          # "llm" | "keyword"


#Synonym / abbreviation map 
# Maps normalised lowercase variant → canonical form.
# Both sides are added so matching works either way.

def _normalise(skill: str) -> str:
    """Lowercase, strip punctuation noise, apply synonym map."""
    # Remove content in parentheses, e.g., "ETL (Extract, Transform, Load)" -> "ETL"
    s = re.sub(r'\s*\([^)]*\)', '', skill).strip()
    s_lower = s.lower().strip(" .,;:-")
    return _SYNONYMS.get(s_lower, s_lower)


def _normalise_set(skills: List[str]) -> Set[str]:
    """Normalises a list of skills to a set of canonical forms."""
    return {_normalise(s) for s in skills if s and s.strip()}




def _extract_keywords(text: str) -> Set[str]:
    text_lower = text.lower()
    found: Set[str] = set()

    for phrase in _MULTI_WORD_SKILLS:
        if phrase in text_lower:
            found.add(phrase)
            text_lower = text_lower.replace(phrase, " ")

    for tok in re.findall(r"[a-z][a-z0-9#\+\.\-\/]*", text_lower):
        # Post-process token to remove trailing punctuation that the regex might include
        cleaned_tok = tok.strip(".,;")
        if len(cleaned_tok) >= 2 and cleaned_tok not in _STOP:
            found.add(cleaned_tok)

    return found


#matching logic

def _compute_match(
    resume_norm: Set[str],
    jd_norm:     Set[str],
    jd_display:  List[str],
    resume_display: List[str],
    method: str,
) -> JobMatchResult:
    if not jd_norm:
        return JobMatchResult(
            matched_skills=[],
            missing_skills=[],
            extra_skills=sorted(resume_display),
            score=0.0,
            score_pct=0.0,
            extraction_method=method,
        )

    matched_norm  = resume_norm & jd_norm
    missing_norm  = jd_norm - resume_norm
    extra_norm    = resume_norm - jd_norm

    # Map normalised back to display strings from jd_display / resume_display
    jd_display_map     = {_normalise(s): s for s in jd_display}
    resume_display_map = {_normalise(s): s for s in resume_display}

    matched = sorted({jd_display_map.get(n, n) for n in matched_norm})
    missing = sorted({jd_display_map.get(n, n) for n in missing_norm})
    extra   = sorted({resume_display_map.get(n, n) for n in extra_norm})

    score = len(matched_norm) / len(jd_norm)

    return JobMatchResult(
        matched_skills=matched,
        missing_skills=missing,
        extra_skills=extra,
        score=round(score, 4),
        score_pct=round(score * 100, 1),
        extraction_method=method,
    )


#Public API

def match_job(
    resume_skills: List[str],
    resume_text:   str,
    jd_text:       str,
    jd_skills_llm: Optional[List[str]] = None,   # pre-extracted by LLM
) -> JobMatchResult:
    """
    Compare resume against a job description.

    When `jd_skills_llm` is provided (LLM-extracted):
      - Match normalised JD skills vs normalised resume skills.
      - Synonym map handles AWS ↔ "Amazon Web Services", JS ↔ JavaScript, etc.

    When `jd_skills_llm` is None (fallback):
      - Extract keywords from raw JD text and raw resume text.
    """
    if jd_skills_llm is not None:
        #LLM path
        # The resume_skills from the parser are often incomplete.
        # Use the keyword extractor on the full resume text for a more comprehensive skill set.
        resume_kw = _extract_keywords(" ".join(resume_skills) + " " + resume_text)
        resume_norm = _normalise_set(list(resume_kw))
        jd_norm     = _normalise_set(jd_skills_llm)
        return _compute_match(
            resume_norm=resume_norm,
            jd_norm=jd_norm,
            jd_display=jd_skills_llm,
            resume_display=sorted(resume_kw),
            method="llm",
        )
    else:
        #Keyword fallback 
        resume_kw = _extract_keywords(" ".join(resume_skills) + " " + resume_text)
        jd_kw     = _extract_keywords(jd_text)
        resume_norm = {_normalise(k) for k in resume_kw}
        jd_norm     = {_normalise(k) for k in jd_kw}
        return _compute_match(
            resume_norm=resume_norm,
            jd_norm=jd_norm,
            jd_display=sorted(jd_kw),
            resume_display=sorted(resume_kw),
            method="keyword",
        )
