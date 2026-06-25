"""
FastAPI application — Hybrid Resume Parser API.

Endpoints:
  GET  /                        health check
  POST /parse-resume-hybrid     single file, hybrid or traditional-only
  POST /parse-resume-batch      up to 10 files, concurrent
  POST /match-job               resume file + job description → skill match
"""

import asyncio
import os
import tempfile
from typing import Annotated, List
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile

from utils.file_extractor import extract_text_from_pdf, extract_text_from_docx, extract_text_from_txt
from llm_parser import LLMParser
from lexer import Lexer
from parser import ResumeParser
from merger import merge, traditional_only, ParseResponse
from job_matcher import match_job, JobMatchResult

load_dotenv()

llm_parser = LLMParser(
    api_key=os.getenv("GROQ_API_KEY"),
    model=os.getenv("LLM_MODEL", "llama-3.1-8b-instant"),
)

app = FastAPI(
    title="Hybrid Resume Parser",
    description=(
        "Combines traditional lexer/parser/AST with LLM-assisted extraction. "
        "Supports single-file hybrid parsing, batch processing, and job-description matching."
    ),
    version="1.0.0",
)

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".rtf"}
MAX_FILE_SIZE  = int(os.getenv("MAX_FILE_SIZE", 10_000_000))   # 10 MB
MAX_BATCH_SIZE = 10


#Shared helpers       

def _validate_upload(file: UploadFile) -> str:
    """Return the lowercased extension or raise HTTPException."""
    ext = os.path.splitext(file.filename or "")[-1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file format: {ext}")
    if file.size is not None and file.size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File size exceeds 10MB limit")
    return ext


async def _extract_text(file: UploadFile, ext: str) -> str:
    """Read upload → temp file → plain text."""
    await file.seek(0)
    contents = await file.read()

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(contents)
            tmp_path = tmp.name

        if ext == ".pdf":
            return extract_text_from_pdf(tmp_path)
        elif ext == ".docx":
            return extract_text_from_docx(tmp_path)
        else:
            return extract_text_from_txt(tmp_path)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract text: {e}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


def _parse_text(text: str, use_llm: bool) -> ParseResponse:
    """Run traditional (+ optionally LLM) parser and merge results."""
    if not text.strip():
        raise HTTPException(status_code=400, detail="File appears to be empty or unreadable.")

    tokens     = Lexer().tokenize(text)
    trad_result = ResumeParser().build(tokens=tokens)

    if use_llm:
        try:
            llm_result = llm_parser.parse_with_llm(text)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"LLM parsing failed: {e}")
        return merge(trad_result, llm_result)
    else:
        return traditional_only(trad_result)


#Endpoints

@app.get("/", summary="Health check")
def home():
    return {"status": "ok"}


@app.post(
    "/parse-resume-hybrid",
    response_model=ParseResponse,
    summary="Parse a single resume (hybrid or traditional-only)",
)
async def parse_resume_hybrid(
    file: UploadFile = File(...),
    use_llm: bool = Query(default=True, description="Enable LLM-assisted parsing"),
):
    ext  = _validate_upload(file)
    text = await _extract_text(file, ext)
    return _parse_text(text, use_llm)


@app.post(
    "/match-job",
    response_model=JobMatchResult,
    summary="Match a resume against a job description",
)
async def match_job_endpoint(
    file: Annotated[UploadFile, File(description="Resume file (PDF / DOCX / TXT / RTF)")],
    job_description: Annotated[str, Form(description="Job description text")],
    use_llm: bool = Query(default=True, description="Use LLM to extract resume skills and JD skills"),
):
    ext  = _validate_upload(file)
    text = await _extract_text(file, ext)

    # Parse resume (always runs traditional; LLM fills gaps when use_llm=True)
    parse_result  = _parse_text(text, use_llm)
    resume_skills = parse_result.merged_result.skills

    # Extract JD skills via LLM (much more accurate than keyword heuristics)
    jd_skills_llm = None
    if use_llm:
        try:
            jd_skills_llm = llm_parser.extract_jd_skills(job_description)
        except Exception:
            jd_skills_llm = None   # fall through to keyword mode silently

    return match_job(
        resume_skills=resume_skills,
        resume_text=text,
        jd_text=job_description,
        jd_skills_llm=jd_skills_llm,
    )