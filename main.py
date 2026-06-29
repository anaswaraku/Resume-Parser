import os
import tempfile
from typing import List, Optional, Annotated

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Query, UploadFile, Form
from pydantic import BaseModel

from job_matcher import JobMatchResult, match_job
from lexer import Lexer
from llm_parser import LLMParser
from merger import merge, traditional_only
from parser import ResumeParser
from utils.file_extractor import (
    extract_text_from_docx,
    extract_text_from_pdf,
    extract_text_from_txt,
)

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


def _extract_text_from_file(ext: str, file_path: str) -> str:
    """Dispatch to the correct extractor based on file extension."""
    if ext == ".pdf":
        return extract_text_from_pdf(file_path)  # type: ignore
    if ext == ".docx":
        return extract_text_from_docx(file_path)  # type: ignore
    return extract_text_from_txt(file_path)  # .txt or .rtf  # type: ignore


async def _extract_text_from_upload(file: UploadFile) -> str:
    """Validate, read, and extract plain text from an uploaded file."""
    ext = os.path.splitext(file.filename or "")[-1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file format: {ext}")

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds {MAX_FILE_SIZE // 1_000_000}MB limit",
        )

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(contents)
            tmp_path = tmp.name

        text = _extract_text_from_file(ext, tmp_path)

    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract text: {e}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    if not text.strip():
        raise HTTPException(
            status_code=400, detail="File appears to be empty or unreadable."
        )
    return text


def _parse_resume(resume_text: str, use_llm: bool):
    """
    Run the full resume parsing pipeline (traditional → optional LLM merge).

    Returns the merged or traditional-only parsed result.
    This is the single source of truth for the tokenise → parse → merge sequence.
    """
    tokens = Lexer().tokenize(resume_text)
    traditional_result = ResumeParser().build(tokens=tokens, raw_text=resume_text)

    if use_llm:
        llm_result = llm_parser.parse_with_llm(resume_text)
        return merge(traditional=traditional_result, llm=llm_result)

    return traditional_only(traditional=traditional_result)


def _extract_jd_skills(jd_text: str, use_llm: bool) -> Optional[List[str]]:
    """Extract job description skills via LLM when enabled, otherwise return None."""
    if use_llm:
        return llm_parser.extract_jd_skills_with_llm(jd_text)
    return None


def _build_match_result(
    file: UploadFile,
    resume_text: str,
    job_description: str,
    use_llm: bool,
    jd_skills_list: Optional[List[str]],
) -> JobMatchResult:
    """
    Parse a single resume and run job matching against the provided JD.

    Accepts pre-computed `jd_skills_list` so batch callers can extract JD
    skills once and reuse across all files.
    """
    parsed = _parse_resume(resume_text, use_llm)
    return match_job(
        resume_skills=parsed.merged_result.skills,
        resume_text=resume_text,
        jd_text=job_description,
        jd_skills_llm=jd_skills_list,
    )


# Endpoints


@app.get("/", tags=["Status"])
def home():
    return {"status": "ok"}


@app.post("/parse-resume-hybrid", tags=["Parsing"])
async def parse_resume_hybrid(
    file: UploadFile = File(...),
    use_llm: bool = Query(default=True),
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
    text = await _extract_text_from_upload(file)
    try:
        return _parse_resume(text, use_llm)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hybrid parsing failed: {e}")


@app.post("/match-job", response_model=JobMatchResult, tags=["Matching"])
async def match_job_endpoint(
    file: Annotated[
        UploadFile, File(description="Resume file (PDF / DOCX / TXT / RTF)")
    ],
    job_description: Annotated[str, Form(description="Job description text")],
    use_llm: bool = Query(
        default=True, description="Use LLM to extract resume skills and JD skills"
    ),
):
    """
    Matches a resume file against a job description.

    The matching process can use two paths:
    - **LLM Path**: If `use_llm` is True, it extracts JD skills using an LLM and uses a sophisticated
      fuzzy token-overlap comparison between the LLM-extracted JD skills and
      an augmented list of resume skills.
    - **Keyword Fallback Path**: If `use_llm` is False, it performs
      keyword extraction on the job description and matches against the resume skills.

    Returns a `JobMatchResult` with matched, missing, and extra skills,
    along with a match score.
    """
    try:
        resume_text = await _extract_text_from_upload(file)
        jd_skills_list = _extract_jd_skills(job_description, use_llm)
        return _build_match_result(
            file, resume_text, job_description, use_llm, jd_skills_list
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {e}")


@app.post("/parse-resume-batch", tags=["Parsing"])
async def parse_resume_batch(
    files: List[UploadFile] = File(...),
    use_llm: bool = Query(default=True),
):
    results = {}
    for file in files:
        filename = file.filename or "unknown"
        try:
            results[filename] = {
                "status": "success",
                "data": await parse_resume_hybrid(file, use_llm),
            }
        except HTTPException as e:
            results[filename] = {"status": "error", "detail": e.detail}
        except Exception as e:
            results[filename] = {"status": "error", "detail": str(e)}
    return results


@app.post("/match-job-batch", tags=["Matching"])
async def match_job_batch_endpoint(
    files: Annotated[
        list[UploadFile],
        File(description="Up to 10 resume files (PDF / DOCX / TXT / RTF)"),
    ],
    job_description: Annotated[str, Form(description="Job description text")],
    use_llm: bool = Query(
        default=True, description="Use LLM to extract resume skills and JD skills"
    ),
):
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 files allowed")

    # Extract JD skills once and reuse across all files (avoids redundant LLM calls)
    jd_skills_list = _extract_jd_skills(job_description, use_llm)

    results = []
    errors = []
    for file in files:
        filename = file.filename or "unknown"
        try:
            resume_text = await _extract_text_from_upload(file)
            match_res = _build_match_result(
                file, resume_text, job_description, use_llm, jd_skills_list
            )
            results.append({"filename": filename, "match": match_res})
        except Exception as e:
            # Instead of silently skipping, record the error
            errors.append(
                {
                    "filename": filename,
                    "error": str(e) if not isinstance(e, HTTPException) else e.detail,
                }
            )

    sorted_results = sorted(results, key=lambda x: x["match"].score, reverse=True)
    best_match = sorted_results[0]["filename"] if sorted_results else None

    return {"best_match": best_match, "results": sorted_results, "errors": errors}
