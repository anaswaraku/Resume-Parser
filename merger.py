"""
Result Merging (FR-09 / FR-10) + Confidence Scoring.

Merge strategy:
  - LLM overrides traditional for name / email / phone.
  - Education / experience: appended from both, fuzzy-deduplicated
    (word-overlap >= 50% on school or company+role). LLM entries preferred
    when duplicates are detected (cleaner formatting).
  - Skills: LLM skills preferred when available (traditional skill
    extraction tends to include category labels and non-skill content).
"""

from __future__ import annotations

import re
from typing import List
from ast_models import Education, Experience, ResumeAST
from llm_parser import ResumeData
from pydantic import BaseModel


# ── Word-overlap utility ─────────────────────────────────────────────────────

def _word_set(text: str) -> set[str]:
    """Lowercase alpha tokens (>=2 chars) extracted from *text*."""
    return {w for w in re.findall(r'[a-zA-Z]{2,}', text.lower())}


def _word_overlap(a: str, b: str) -> float:
    """Fraction of the smaller word-set that overlaps with the other."""
    wa, wb = _word_set(a), _word_set(b)
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / min(len(wa), len(wb))


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


def _data_to_merged(data: ResumeData) -> MergedResult:
    return MergedResult(
        name=data.name, email=data.email, phone=data.phone,
        education=data.education, experience=data.experience,
        skills=data.skills,
    )


def _dedupe_skills(skills: List[str]) -> List[str]:
    seen: set[str] = set()
    result: List[str] = []
    for s in skills:
        key = s.strip().lower()
        if key and key not in seen:
            seen.add(key)
            result.append(s.strip())
    return result


# ── Education / Experience merge (fuzzy dedup) ────────────────────────────────

_OVERLAP_THRESHOLD = 0.5   # 50% word overlap -> same entity


def _merge_education(trad: List[Education], llm: List[Education]) -> List[Education]:
    """LLM entries first (cleaner). Traditional entries added only when they
    don't fuzzy-match any LLM entry (by school name word overlap)."""
    result = list(llm)
    for t in trad:
        is_dup = any(
            _word_overlap(t.school or "", l.school or "") >= _OVERLAP_THRESHOLD
            for l in llm
        )
        if not is_dup:
            result.append(t)
    return result


def _merge_experience(trad: List[Experience], llm: List[Experience]) -> List[Experience]:
    """LLM entries first (cleaner). Traditional entries added only when they
    don't fuzzy-match any LLM entry (by combined company+role word overlap)."""
    result = list(llm)
    for t in trad:
        t_text = f"{t.company or ''} {t.role or ''}"
        is_dup = any(
            _word_overlap(t_text, f"{l.company or ''} {l.role or ''}") >= _OVERLAP_THRESHOLD
            for l in llm
        )
        if not is_dup:
            result.append(t)
    return result


# ── Skills merge ──────────────────────────────────────────────────────────────

def _merge_skills(trad: List[str], llm: List[str]) -> List[str]:
    """LLM skills preferred (cleaner extraction). Traditional skills used
    only as fallback when LLM found nothing."""
    if llm:
        return _dedupe_skills(llm)
    return _dedupe_skills(trad)


# ── Confidence scoring ────────────────────────────────────────────────────────

def _edu_key(e: Education) -> str:
    return f"{(e.degree or '').lower().strip()}|{(e.school or '').lower().strip()}"


def _exp_key(e: Experience) -> str:
    return f"{(e.company or '').lower().strip()}|{(e.role or '').lower().strip()}"


def _compute_confidence(
    traditional: ResumeAST,
    llm: ResumeData,
    merged_edu: List[Education],
    merged_exp: List[Experience],
    merged_skills: List[str],
) -> ConfidenceScore:
    name_from_llm  = bool(llm.name)
    email_from_llm = bool(llm.email)
    phone_from_llm = bool(llm.phone)

    trad_edu_keys = {_edu_key(e) for e in traditional.education}
    edu_added = sum(1 for e in merged_edu if _edu_key(e) not in trad_edu_keys)

    trad_exp_keys = {_exp_key(e) for e in traditional.experience}
    exp_added = sum(1 for e in merged_exp if _exp_key(e) not in trad_exp_keys)

    trad_skill_keys = {s.lower() for s in traditional.skills}
    skills_added = sum(1 for s in merged_skills if s.lower() not in trad_skill_keys)

    improved_slots = sum([
        not traditional.name  and bool(llm.name),
        not traditional.email and bool(llm.email),
        not traditional.phone and bool(llm.phone),
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

def merge(traditional: ResumeAST, llm: ResumeData) -> ParseResponse:
    """Merge traditional + LLM results into the full ParseResponse."""
    trad_view = _ast_to_merged(traditional)
    llm_view  = _data_to_merged(llm)

    # Contact: LLM overrides (FR-09)
    merged_name  = llm.name  or traditional.name
    merged_email = llm.email or traditional.email
    merged_phone = llm.phone or traditional.phone

    # Education / experience: append + fuzzy dedup, LLM preferred
    merged_edu = _merge_education(traditional.education, llm.education)
    merged_exp = _merge_experience(traditional.experience, llm.experience)

    # Skills: LLM preferred
    merged_skills = _merge_skills(traditional.skills, llm.skills)

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
