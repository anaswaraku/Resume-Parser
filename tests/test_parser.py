import pytest
from fastapi.testclient import TestClient

from main import app, _parse_resume

client = TestClient(app)

def test_tc01_email_extraction_traditional():
    """
    TC-01: Email Extraction (Traditional Parser)
    Input: Resume text containing "john@example.com"
    Expected: merged_result.email = "john@example.com"
    Parser: Traditional only
    """
    text = "John Doe\njohn@example.com\n123-456-7890\nSkills: Python, Java"
    result = _parse_resume(text, use_llm=False)
    assert result.merged_result.email == "john@example.com"


def test_tc05_unsupported_file_format():
    """
    TC-05: Unsupported File Format
    Input: Upload .exe file
    Expected: 400 Bad Request with error message
    Parser: N/A (pre-validation)
    """
    file_content = b"MZ\x90\x00..."
    response = client.post(
        "/parse-resume-hybrid",
        files={"file": ("virus.exe", file_content, "application/x-msdownload")}
    )
    assert response.status_code == 400
    assert "Unsupported file format: .exe" in response.json()["detail"]


# --- Legacy scratchpad code ---
if __name__ == "__main__":
    from utils.file_extractor import extract_text_from_txt
    from lexer import Lexer
    from parser import LineBuilder, HeaderBuilder, ResumeParser
    
    txt = extract_text_from_txt("resumes/resume.txt")
    t = Lexer()
    token = t.tokenize(txt)
    
    l = LineBuilder()
    print(ResumeParser().build(tokens=token))