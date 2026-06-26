import os
import tempfile
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from pydantic import BaseModel

from job_matcher import JobMatchResult, match_job
from lexer import Lexer
from llm_parser import LLMParser
from merger import merge, traditional_only
from parser import ResumeParser
from utils.file_extractor import (extract_text_from_docx,
                                  extract_text_from_pdf, extract_text_from_txt)

load_dotenv()

app = FastAPI(
    title="Resume Parser and Job Matcher API",
    description="An API to parse resumes and match them against job descriptions.",
)

llm_parser = LLMParser(
    api_key=os.getenv("GROQ_API_KEY"),
    model=os.getenv("LLM_MODEL", "llama3-8b-8192"),
)

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".rtf"}
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 10_000_000))


class JobMatchRequest(BaseModel):
    """Request body for the job matching endpoint."""
    resume_skills: List[str]
    resume_text:   str
    jd_text:       str
    jd_skills_llm: Optional[List[str]] = None


@app.get("/", tags=["Status"])
def home():
    return {"status": "ok"}


@app.post("/parse-resume-hybrid", tags=["Parsing"])
async def parse_resume_hybrid(
    file: UploadFile = File(...),
    use_llm: bool = Query(default=True)
):
    """
    Parses a resume file using a hybrid approach (traditional + LLM).

    - **Traditional Parser**: Extracts basic entities like email, phone, and
      identifies sections based on keywords.
    - **LLM Parser**: Extracts more complex and contextual information like
      full education/experience entries and skills.
    - **Merging**: Combines results, with LLM data filling gaps or overriding
      where it provides cleaner output.

    Set `use_llm=false` to disable the LLM and see only the traditional parser's output.
    """
    # Validate extension
    ext = os.path.splitext(file.filename or "")[-1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file format: {ext}")

    # Read file and validate size
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"File size exceeds {MAX_FILE_SIZE // 1000000}MB limit")

    tmp_path = None
    try:
        # Write to a temporary file because some extractors need a file path
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(contents)
            tmp_path = tmp.name

        # Extract plain text based on file type
        if ext == ".pdf":
            text = extract_text_from_pdf(tmp_path)  # type: ignore
        elif ext == ".docx":
            text = extract_text_from_docx(tmp_path)  # type: ignore
        else:  # .txt or .rtf
            text = extract_text_from_txt(tmp_path)  # type: ignore

    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract text: {e}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    if not text.strip():
        raise HTTPException(status_code=400, detail="File appears to be empty or unreadable.")

    # Always run the traditional parser first
    tokens = Lexer().tokenize(text)
    traditional_result = ResumeParser().build(tokens=tokens)

    if use_llm:
        try:
            llm_result = llm_parser.parse_with_llm(text)
            return merge(traditional=traditional_result, llm=llm_result)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Hybrid parsing failed: {e}")
    else:
        # Return only the result from the traditional parser
        return traditional_only(traditional=traditional_result)


@app.post("/match-job", response_model=JobMatchResult, tags=["Matching"])
async def match_job_endpoint(request: JobMatchRequest):
    """
    Matches a resume against a job description.

    The matching process can use two paths:
    - **LLM Path**: If `jd_skills_llm` is provided, it uses a sophisticated
      fuzzy token-overlap comparison between the LLM-extracted JD skills and
      an augmented list of resume skills.
    - **Keyword Fallback Path**: If `jd_skills_llm` is omitted, it performs
      keyword extraction on the job description and matches against the resume skills.

    Returns a `JobMatchResult` with matched, missing, and extra skills,
    along with a match score.
    """
    try:
        match_result = match_job(
            resume_skills=request.resume_skills,
            resume_text=request.resume_text,
            jd_text=request.jd_text,
            jd_skills_llm=request.jd_skills_llm,
        )
        return match_result
    except Exception as e:
        # In a production environment, you would want to log this exception.
        # import logging
        # logging.exception("An error occurred during job matching.")
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {e}")