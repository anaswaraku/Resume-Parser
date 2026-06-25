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


#Response model ────────────────────────────────────────────────────────────

class JobMatchResult(BaseModel):
    matched_skills: List[str]
    missing_skills: List[str]
    extra_skills:   List[str]       # on resume but not required by JD
    score:          float           # 0.0 – 1.0
    score_pct:      float           # 0.0 – 100.0
    extraction_method: str          # "llm" | "keyword"


#Synonym / abbreviation map ────────────────────────────────────────────────
# Maps normalised lowercase variant → canonical form.
# Both sides are added so matching works either way.

_SYNONYMS: dict[str, str] = {
    # Languages
    "js":                    "javascript",
    "ts":                    "typescript",
    "py":                    "python",
    "rb":                    "ruby",
    "golang":                "go",
    # Cloud
    "aws":                   "amazon web services",
    "amazon web services":   "aws",
    "gcp":                   "google cloud platform",
    "google cloud":          "google cloud platform",
    "azure":                 "microsoft azure",
    # ML / AI
    "ml":                    "machine learning",
    "dl":                    "deep learning",
    "ai":                    "artificial intelligence",
    "nlp":                   "natural language processing",
    "cv":                    "computer vision",
    "gen ai":                "generative ai",
    "llm":                   "large language model",
    # DevOps
    "k8s":                   "kubernetes",
    "ci/cd":                 "continuous integration",
    "ci cd":                 "continuous integration",
    # Frameworks / libs
    "react":                 "reactjs",
    "react.js":              "reactjs",
    "react js":              "reactjs",
    "vue":                   "vuejs",
    "vue.js":                "vuejs",
    "node":                  "nodejs",
    "node.js":               "nodejs",
    "next":                  "nextjs",
    "next.js":               "nextjs",
    "express":               "expressjs",
    "express.js":            "expressjs",
    "fast api":              "fastapi",
    "spring":                "spring boot",
    # Databases
    "postgres":              "postgresql",
    "mongo":                 "mongodb",
    "es":                    "elasticsearch",
    # Practices
    "oop":                   "object oriented programming",
    "tdd":                   "test driven development",
    "bdd":                   "behavior driven development",
    "rest":                  "rest api",
    "restful":               "rest api",
    "graphql":               "graphql api",
    # Misc
    "dot net":               ".net",
    "dotnet":                ".net",
    "asp.net":               ".net",
    "tf":                    "tensorflow",
    "pt":                    "pytorch",
}


def _normalise(skill: str) -> str:
    """Lowercase, strip punctuation noise, apply synonym map."""
    s = skill.lower().strip(" .,;:-")
    return _SYNONYMS.get(s, s)


def _normalise_set(skills: List[str]) -> Set[str]:
    result = set()
    for s in skills:
        n = _normalise(s)
        result.add(n)
        # Also add synonym expansions so matching works both directions
        if n in _SYNONYMS:
            result.add(_SYNONYMS[n])
    return result


#Keyword extraction fallback ───────────────────────────────────────────────

_STOP = {
    "the","and","or","a","an","in","on","at","to","for","of","with",
    "is","are","be","we","you","your","our","will","must","should","can",
    "have","has","this","that","as","from","by","not","but","if","it",
    "its","etc","including","such","other","any","all","both","each",
    "more","also","than","then","when","where","how","what","who","which",
    "about","into","through","during","before","after","above","below",
    "between","up","down","out","off","over","under","again","further",
    "once","experience","working","work","ability","strong","knowledge",
    "using","use","used","good","excellent","required","preferred",
    "minimum","years","year","plus","role","team","company","position",
    "candidate","responsibilities","qualifications","requirement",
}

_MULTI_WORD_SKILLS = [
    "machine learning","deep learning","natural language processing",
    "computer vision","data science","data engineering","cloud computing",
    "distributed systems","continuous integration","continuous deployment",
    "test driven development","behavior driven development",
    "object oriented programming","functional programming",
    "restful api","rest api","graphql api","google cloud platform",
    "amazon web services","microsoft azure",
    "spring boot","node js","next js","react js","vue js",
]


def _extract_keywords(text: str) -> Set[str]:
    text_lower = text.lower()
    found: Set[str] = set()

    for phrase in _MULTI_WORD_SKILLS:
        if phrase in text_lower:
            found.add(phrase)
            text_lower = text_lower.replace(phrase, " ")

    for tok in re.findall(r"[a-z][a-z0-9#\+\.\-\/]*", text_lower):
        if len(tok) >= 2 and tok not in _STOP:
            found.add(tok)

    return found


#Core matching logic ───────────────────────────────────────────────────────

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


#Public API ────────────────────────────────────────────────────────────────

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
        #LLM path ─────────────────────────────────────────────────────────
        resume_norm = _normalise_set(resume_skills)
        jd_norm     = _normalise_set(jd_skills_llm)
        return _compute_match(
            resume_norm=resume_norm,
            jd_norm=jd_norm,
            jd_display=jd_skills_llm,
            resume_display=resume_skills,
            method="llm",
        )
    else:
        #Keyword fallback ─────────────────────────────────────────────────
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
