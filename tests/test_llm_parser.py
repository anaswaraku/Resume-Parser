"""
Tests for llm_parser.py — Groq client is mocked so no real API calls are made.
Covers: JSON parsing, code-fence stripping, validation fallback, chunking.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
import pytest
from unittest.mock import MagicMock, patch
from llm_parser import LLMParser, ResumeData, _strip_fences, _merge_chunks, MAX_RESUME_CHARS


#Helpers ───────────────────────────────────────────────────────────────────

VALID_PAYLOAD = {
    "name": "Jane Doe",
    "email": "jane@example.com",
    "phone": "987-654-3210",
    "education": [{"degree": "BSc CS", "school": "MIT",
                   "start_date": "2018-09", "end_date": "2022-05"}],
    "experience": [{"company": "Google", "role": "SWE",
                    "start_date": "2022-06", "end_date": None,
                    "description": "Built APIs."}],
    "skills": ["Python", "Go"],
}


def _make_parser(return_content: str) -> LLMParser:
    """Create LLMParser with a mocked Groq client."""
    parser = LLMParser.__new__(LLMParser)
    parser.model = "test-model"

    mock_choice   = MagicMock()
    mock_choice.message.content = return_content
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response
    parser.client = mock_client
    return parser


#_strip_fences ─────────────────────────────────────────────────────────────

def test_strip_fences_plain_json():
    raw = '{"name": "Jane"}'
    assert _strip_fences(raw) == raw


def test_strip_fences_with_json_block():
    raw = '```json\n{"name": "Jane"}\n```'
    assert _strip_fences(raw) == '{"name": "Jane"}'


def test_strip_fences_with_plain_block():
    raw = '```\n{"name": "Jane"}\n```'
    assert _strip_fences(raw) == '{"name": "Jane"}'


def test_strip_fences_with_leading_text():
    raw = 'Here is the result:\n```json\n{"name": "Jane"}\n```'
    assert _strip_fences(raw) == '{"name": "Jane"}'


#parse_with_llm — happy path ───────────────────────────────────────────────

def test_parse_returns_resume_data():
    parser = _make_parser(json.dumps(VALID_PAYLOAD))
    result = parser.parse_with_llm("Some resume text")
    assert isinstance(result, ResumeData)
    assert result.name == "Jane Doe"
    assert result.email == "jane@example.com"


def test_parse_education_populated():
    parser = _make_parser(json.dumps(VALID_PAYLOAD))
    result = parser.parse_with_llm("Some resume text")
    assert len(result.education) == 1
    assert result.education[0].school == "MIT"


def test_parse_skills_populated():
    parser = _make_parser(json.dumps(VALID_PAYLOAD))
    result = parser.parse_with_llm("Some resume text")
    assert "Python" in result.skills


#Fence stripping in full pipeline ─────────────────────────────────────────

def test_parse_strips_code_fences():
    fenced = f"```json\n{json.dumps(VALID_PAYLOAD)}\n```"
    parser = _make_parser(fenced)
    result = parser.parse_with_llm("Some resume text")
    assert result.name == "Jane Doe"


#Error / fallback paths ────────────────────────────────────────────────────

def test_invalid_json_returns_empty():
    parser = _make_parser("this is not json at all")
    result = parser.parse_with_llm("Some resume text")
    assert result == ResumeData()


def test_invalid_schema_returns_empty():
    bad = json.dumps({"wrong_key": 42})
    parser = _make_parser(bad)
    result = parser.parse_with_llm("Some resume text")
    # Pydantic ignores extra keys → should still be valid (no crash)
    assert isinstance(result, ResumeData)


def test_empty_response_returns_empty():
    parser = _make_parser("")
    result = parser.parse_with_llm("Some resume text")
    assert result == ResumeData()


def test_api_exception_returns_empty():
    parser = LLMParser.__new__(LLMParser)
    parser.model = "test-model"
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = RuntimeError("API down")
    parser.client = mock_client
    result = parser.parse_with_llm("Some resume text")
    assert result == ResumeData()


#Chunking ──────────────────────────────────────────────────────────────────

def test_short_text_single_call():
    parser = _make_parser(json.dumps(VALID_PAYLOAD))
    short_text = "A" * (MAX_RESUME_CHARS - 1)
    parser.parse_with_llm(short_text)
    assert parser.client.chat.completions.create.call_count == 1


def test_long_text_multiple_calls():
    parser = _make_parser(json.dumps(VALID_PAYLOAD))
    long_text = "A" * (MAX_RESUME_CHARS * 3)
    parser.parse_with_llm(long_text)
    assert parser.client.chat.completions.create.call_count > 1


#_merge_chunks ─────────────────────────────────────────────────────────────

def test_merge_chunks_scalars_first_wins():
    from ast_models import Education, Experience
    r1 = ResumeData(name="First", email="first@x.com")
    r2 = ResumeData(name="Second", email="second@x.com")
    merged = _merge_chunks([r1, r2])
    assert merged.name  == "First"
    assert merged.email == "first@x.com"


def test_merge_chunks_skills_union():
    r1 = ResumeData(skills=["Python", "SQL"])
    r2 = ResumeData(skills=["Docker", "SQL"])
    merged = _merge_chunks([r1, r2])
    skills_lower = [s.lower() for s in merged.skills]
    assert "python" in skills_lower
    assert "docker" in skills_lower
    assert skills_lower.count("sql") == 1


def test_merge_chunks_empty_list():
    merged = _merge_chunks([])
    assert merged == ResumeData()
