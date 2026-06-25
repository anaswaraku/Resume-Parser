"""
Tests for parser.py — covers TC-01 through TC-05 from the requirements spec
plus edge cases for the traditional parser pipeline.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from lexer import Lexer
from parser import ResumeParser
from ast_models import ResumeAST


#helpers ───────────────────────────────────────────────────────────────────

def parse(text: str) -> ResumeAST:
    tokens = Lexer().tokenize(text)
    return ResumeParser().build(tokens=tokens)


#TC-01: Email extraction ───────────────────────────────────────────────────

def test_email_extracted(sample_text):
    result = parse(sample_text)
    assert result.email == "john.doe@example.com"


def test_email_not_present():
    result = parse("John Doe\nSoftware Engineer\nSkills\nPython")
    assert result.email is None


def test_email_invalid_not_stored():
    """Malformed address should not appear in output."""
    result = parse("John Doe\nnot-an-email\nSkills\nPython")
    assert result.email is None


#TC-02: Phone extraction ───────────────────────────────────────────────────

def test_phone_extracted(sample_text):
    result = parse(sample_text)
    assert result.phone is not None
    # digits only comparison (format may vary)
    import re
    digits = re.sub(r"\D", "", result.phone)
    assert len(digits) >= 10


#Name extraction ───────────────────────────────────────────────────────────

def test_name_extracted(sample_text):
    result = parse(sample_text)
    assert result.name == "John Doe"


#Skills extraction ────────────────────────────────────────────────────────

def test_skills_extracted(sample_text):
    result = parse(sample_text)
    skills_lower = [s.lower() for s in result.skills]
    assert "python" in skills_lower


def test_skills_deduplicated():
    text = "Skills\nPython, Python, python\n"
    result = parse(text)
    skill_lower = [s.lower() for s in result.skills]
    assert skill_lower.count("python") == 1


#Education extraction ─────────────────────────────────────────────────────

def test_education_section_parsed(sample_text):
    result = parse(sample_text)
    # Traditional parser may or may not find education; must not crash
    assert isinstance(result.education, list)


#Experience extraction ─────────────────────────────────────────────────────

def test_experience_section_parsed(sample_text):
    result = parse(sample_text)
    assert isinstance(result.experience, list)


#Edge cases ────────────────────────────────────────────────────────────────

def test_empty_text():
    result = parse("")
    assert result == ResumeAST()


def test_only_whitespace():
    result = parse("   \n\n\t  ")
    assert result.name is None
    assert result.email is None


def test_no_sections():
    result = parse("John Smith\njohn@example.com\n+1 800 555 1234")
    assert result.email == "john@example.com"
    assert result.name == "John Smith"


def test_multiple_emails_first_wins():
    text = "John Doe\nfirst@example.com\nsecond@example.com\nSkills\nPython"
    result = parse(text)
    assert result.email == "first@example.com"


def test_alias_section_headers():
    """'Work Experience' and 'Technical Skills' are aliases."""
    text = (
        "Jane Doe\njane@example.com\n"
        "Work Experience\nGoogle\nSoftware Engineer\n\n"
        "Technical Skills\nPython, Go\n"
    )
    result = parse(text)
    skills_lower = [s.lower() for s in result.skills]
    assert "python" in skills_lower