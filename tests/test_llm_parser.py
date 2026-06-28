import pytest
from unittest.mock import patch

from main import _parse_resume, llm_parser
from ast_models import ResumeAST, Education


@patch.object(llm_parser, 'parse_with_llm')
def test_tc02_name_extraction_llm(mock_llm):
    """
    TC-02: Name Extraction (LLM Parser)
    Input: Resume starting with "John Doe - Software Engineer"
    Expected: merged_result.name = "John Doe"
    Parser: LLM only
    """
    mock_llm.return_value = ResumeAST(name="John Doe")
    text = "John Doe - Software Engineer\n"
    
    result = _parse_resume(text, use_llm=True)
    assert result.merged_result.name == "John Doe"

@patch.object(llm_parser, 'parse_with_llm')
def test_tc03_education_extraction_llm(mock_llm):
    """
    TC-03: Education Extraction (LLM Parser)
    Input: Section "Education: BSc Computer Science, XYZ University, 2018-2022"
    Expected: merged_result.education = [{"degree": "BSc...", "school": "XYZ...", ...}]
    Parser: LLM only
    """
    mock_ed = Education(
        degree="BSc Computer Science", 
        school="XYZ University", 
        start_date="2018", 
        end_date="2022"
    )
    mock_llm.return_value = ResumeAST(education=[mock_ed])
    text = "Education: BSc Computer Science, XYZ University, 2018-2022"
    
    result = _parse_resume(text, use_llm=True)
    assert len(result.merged_result.education) == 1
    assert result.merged_result.education[0].degree == "BSc Computer Science"
    assert result.merged_result.education[0].school == "XYZ University"

@patch.object(llm_parser, 'parse_with_llm')
def test_tc04_hybrid_merging(mock_llm):
    """
    TC-04: Hybrid Merging
    Input: Traditional extracts email, LLM extracts name
    Expected: merged_result.name and merged_result.email both populated
    Parser: Hybrid
    """
    mock_llm.return_value = ResumeAST(name="John Doe", email=None)
    text = "Resume\njohn@example.com"
    
    result = _parse_resume(text, use_llm=True)
    assert result.merged_result.name == "John Doe"
    assert result.merged_result.email == "john@example.com"
