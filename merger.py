"""
Result Merging (Hybrid approach).

Merge strategy:
  - Traditional parser wins on contact info (name, email, phone) and education.
  - LLM fills in experience and skills (traditional parser leaves these empty).
  - If traditional parser fails to find contact info or education, it falls back to the LLM.
"""

from __future__ import annotations

from typing import List
from ast_models import Education, Experience, ResumeAST
from pydantic import BaseModel


# ── Output models ─────────────────────────────────────────────────────────────

class MergedResult(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    education: List[Education] = []
    experience: List[Experience] = []
    skills: List[str] = []


class ConfidenceScore(BaseModel):
    """Per-field flags showing which fields the LLM contributed."""
    name_from_llm: bool = False
    email_from_llm: bool = False
    phone_from_llm: bool = False
    education_added_by_llm: int = 0
    experience_added_by_llm: int = 0
    skills_added_by_llm: int = 0
    improvement_pct: float = 0.0        # 0-100


class ParseResponse(BaseModel):
    traditional_parser: MergedResult
    llm_parser: MergedResult | None = None
    merged_result: MergedResult
    parsing_method: str                 # "hybrid" | "traditional_only"
    confidence: ConfidenceScore | None = None


# ── Internal helpers ──────────────────────────────────────────────────────────

def _ast_to_merged(ast: ResumeAST) -> MergedResult:
    return MergedResult(
        name=ast.name, email=ast.email, phone=ast.phone,
        education=ast.education, experience=ast.experience,
        skills=ast.skills,
    )


def _compute_confidence(
    traditional: ResumeAST,
    llm: ResumeAST,
    merged_edu: List[Education],
    merged_exp: List[Experience],
    merged_skills: List[str],
) -> ConfidenceScore:
    name_from_llm  = not traditional.name and bool(llm.name)
    email_from_llm = not traditional.email and bool(llm.email)
    phone_from_llm = not traditional.phone and bool(llm.phone)

    # For education, if traditional was empty and we used LLM, then all are from LLM
    edu_added = len(llm.education) if not traditional.education and llm.education else 0
    
    # Experience and skills are always from LLM in the new logic
    exp_added = len(merged_exp)
    skills_added = len(merged_skills)

    improved_slots = sum([
        name_from_llm,
        email_from_llm,
        phone_from_llm,
        bool(edu_added),
        bool(exp_added),
        bool(skills_added),
    ])
    improvement_pct = round(improved_slots / 6 * 100, 1)

    return ConfidenceScore(
        name_from_llm=name_from_llm,
        email_from_llm=email_from_llm,
        phone_from_llm=phone_from_llm,
        education_added_by_llm=edu_added,
        experience_added_by_llm=exp_added,
        skills_added_by_llm=skills_added,
        improvement_pct=improvement_pct,
    )


# ── Public API ────────────────────────────────────────────────────────────────

def merge(traditional: ResumeAST, llm: ResumeAST) -> ParseResponse:
    """Merge traditional + LLM results into the full ParseResponse."""
    trad_view = _ast_to_merged(traditional)
    llm_view  = _ast_to_merged(llm)

    # Traditional wins on contact + education
    merged_name  = traditional.name or llm.name
    merged_email = traditional.email or llm.email
    merged_phone = traditional.phone or llm.phone
    merged_edu   = traditional.education if traditional.education else llm.education

    # LLM always fills experience and skills
    merged_exp = llm.experience
    merged_skills = llm.skills

    merged = MergedResult(
        name=merged_name,
        email=merged_email,
        phone=merged_phone,
        education=merged_edu,
        experience=merged_exp,
        skills=merged_skills,
    )

    confidence = _compute_confidence(
        traditional, llm, merged_edu, merged_exp, merged_skills,
    )

    return ParseResponse(
        traditional_parser=trad_view,
        llm_parser=llm_view,
        merged_result=merged,
        parsing_method="hybrid",
        confidence=confidence,
    )


def traditional_only(traditional: ResumeAST) -> ParseResponse:
    """Wrap a traditional-only parse into the standard ParseResponse shape."""
    view = _ast_to_merged(traditional)
    return ParseResponse(
        traditional_parser=view,
        llm_parser=None,
        merged_result=view,
        parsing_method="traditional_only",
        confidence=None,
    )
