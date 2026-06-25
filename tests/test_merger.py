"""
Tests for merger.py — covers FR-09 (hybrid merging) with fuzzy dedup.

Merge strategy under test:
  - LLM overrides traditional for name / email / phone
  - Education / experience: appended, fuzzy-deduplicated by word overlap
  - Skills: LLM preferred when available, traditional as fallback
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from ast_models import Education, Experience, ResumeAST
from llm_parser import ResumeData
from merger import (
    merge, traditional_only, ConfidenceScore,
    _word_overlap, _merge_education, _merge_experience, _merge_skills,
)


# ── Word-overlap utility ─────────────────────────────────────────────────────

def test_word_overlap_identical():
    assert _word_overlap("Bharata Mata College", "Bharata Mata College") == 1.0


def test_word_overlap_subset():
    # "MIT" has 1 word (3 chars), "MIT University" has 2 words — overlap = 1/1
    assert _word_overlap("MIT University", "MIT Campus") >= 0.5


def test_word_overlap_no_match():
    assert _word_overlap("Google", "Stanford") == 0.0


def test_word_overlap_empty():
    assert _word_overlap("", "anything") == 0.0
    assert _word_overlap("", "") == 0.0


def test_word_overlap_fuzzy_school():
    """Real-world case: traditional school has dates baked in."""
    trad = "Bharata Mata College , Thrikkakara 2021 -26"
    llm  = "Bharata Mata College, Thrikkakara"
    assert _word_overlap(trad, llm) >= 0.5


# ── Contact: LLM overrides traditional ───────────────────────────────────────

def test_merge_llm_overrides_name():
    trad = ResumeAST(name="Trad Name")
    llm  = ResumeData(name="LLM Name")
    result = merge(trad, llm)
    assert result.merged_result.name == "LLM Name"


def test_merge_llm_overrides_email():
    trad = ResumeAST(email="trad@example.com")
    llm  = ResumeData(email="llm@example.com")
    result = merge(trad, llm)
    assert result.merged_result.email == "llm@example.com"


def test_merge_llm_overrides_phone():
    trad = ResumeAST(phone="111-111-1111")
    llm  = ResumeData(phone="999-999-9999")
    result = merge(trad, llm)
    assert result.merged_result.phone == "999-999-9999"


def test_merge_falls_back_to_traditional_when_llm_missing():
    trad = ResumeAST(name="Trad", email="t@x.com", phone="123-456-7890")
    llm  = ResumeData()
    result = merge(trad, llm)
    assert result.merged_result.name  == "Trad"
    assert result.merged_result.email == "t@x.com"
    assert result.merged_result.phone == "123-456-7890"


# ── Education: fuzzy dedup ────────────────────────────────────────────────────

def test_education_distinct_entries_both_kept():
    """Completely different schools are both kept."""
    trad = [Education(degree="BSc CS", school="MIT")]
    llm  = [Education(degree="MSc AI", school="Stanford")]
    result = _merge_education(trad, llm)
    assert len(result) == 2


def test_education_fuzzy_duplicate_keeps_llm():
    """Same school with different formatting → only LLM version kept."""
    trad = [Education(
        degree="Integrated MSc Computer Science",
        school="Bharata Mata College , Thrikkakara 2021 -26",
    )]
    llm = [Education(
        degree="Integrated MSc",
        school="Bharata Mata College, Thrikkakara",
        start_date="2021-01", end_date="2026-01",
    )]
    result = _merge_education(trad, llm)
    assert len(result) == 1
    assert result[0].start_date == "2021-01"   # LLM version preserved


def test_education_llm_has_more_entries():
    """LLM found 3 entries, traditional found 1 (same school). Result = 3."""
    trad = [Education(degree="BSc", school="Bharata Mata College Thrikkakara")]
    llm  = [
        Education(degree="Integrated MSc", school="Bharata Mata College, Thrikkakara"),
        Education(degree="Higher Secondary", school="Govt HSS North Paravoor"),
        Education(degree="SSLC", school="St Augustine GHS Kuzhupilly"),
    ]
    result = _merge_education(trad, llm)
    assert len(result) == 3


def test_education_empty_both():
    assert _merge_education([], []) == []


def test_education_only_traditional():
    trad = [Education(degree="BSc", school="MIT")]
    result = _merge_education(trad, [])
    assert len(result) == 1


# ── Experience: fuzzy dedup ───────────────────────────────────────────────────

def test_experience_distinct_entries_both_kept():
    trad = [Experience(company="Google", role="SWE")]
    llm  = [Experience(company="Meta", role="ML Engineer")]
    result = _merge_experience(trad, llm)
    assert len(result) == 2


def test_experience_fuzzy_duplicate_keeps_llm():
    """Traditional has messy company/role split, LLM has clean one."""
    trad = [Experience(
        company="",
        role="AI Research Intern Talks Talks Technologies Ltd.",
    )]
    llm = [Experience(
        company="Talks & Talks Technologies Ltd.",
        role="AI Research Intern",
    )]
    result = _merge_experience(trad, llm)
    assert len(result) == 1
    assert result[0].company == "Talks & Talks Technologies Ltd."


# ── Skills: LLM preferred ────────────────────────────────────────────────────

def test_skills_llm_preferred_when_available():
    trad = ["Languages Python", "Backend APIs FastAPI", "Extracurricular Activities"]
    llm  = ["Python", "FastAPI", "Docker"]
    result = _merge_skills(trad, llm)
    assert result == ["Python", "FastAPI", "Docker"]


def test_skills_traditional_fallback_when_no_llm():
    trad = ["Python", "SQL"]
    result = _merge_skills(trad, [])
    assert "Python" in result
    assert "SQL" in result


def test_skills_empty_both():
    assert _merge_skills([], []) == []


def test_skills_deduplication():
    trad = []
    llm  = ["Python", "python", "PYTHON"]
    result = _merge_skills(trad, llm)
    assert len([s for s in result if s.lower() == "python"]) == 1


# ── Parsing method flag ───────────────────────────────────────────────────────

def test_merge_sets_hybrid_method():
    result = merge(ResumeAST(), ResumeData())
    assert result.parsing_method == "hybrid"


def test_traditional_only_sets_method():
    result = traditional_only(ResumeAST(email="x@y.com"))
    assert result.parsing_method == "traditional_only"
    assert result.llm_parser is None


def test_traditional_only_no_confidence():
    result = traditional_only(ResumeAST())
    assert result.confidence is None


# ── Confidence scoring ────────────────────────────────────────────────────────

def test_confidence_name_from_llm():
    trad = ResumeAST()
    llm  = ResumeData(name="John")
    result = merge(trad, llm)
    assert result.confidence.name_from_llm is True


def test_confidence_education_added_count():
    trad = ResumeAST()
    llm  = ResumeData(education=[
        Education(degree="BSc", school="MIT"),
        Education(degree="MSc", school="Stanford"),
    ])
    result = merge(trad, llm)
    assert result.confidence.education_added_by_llm == 2


def test_confidence_skills_added_count():
    trad = ResumeAST(skills=["Python"])
    llm  = ResumeData(skills=["Python", "Docker", "SQL"])
    result = merge(trad, llm)
    # LLM skills used exclusively; Docker and SQL are not in traditional
    assert result.confidence.skills_added_by_llm == 2


def test_confidence_improvement_pct_zero():
    edu = Education(degree="BSc", school="MIT")
    exp = Experience(company="Google", role="SWE")
    phone = "123-456-7890"
    trad = ResumeAST(
        name="John", email="j@x.com", phone=phone,
        education=[edu], experience=[exp], skills=["Python"],
    )
    llm = ResumeData(
        name="John", email="j@x.com", phone=phone,
        education=[edu], experience=[exp], skills=["Python"],
    )
    result = merge(trad, llm)
    assert result.confidence.improvement_pct == 0.0


def test_confidence_full_improvement():
    edu = Education(degree="BSc", school="MIT")
    exp = Experience(company="Google", role="SWE")
    trad = ResumeAST()
    llm  = ResumeData(
        name="Jane", email="j@x.com", phone="999",
        education=[edu], experience=[exp], skills=["Python"],
    )
    result = merge(trad, llm)
    assert result.confidence.improvement_pct == 100.0
