from groq import Groq
import json
import logging
import re

from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError
from ast_models import Education, Experience
from typing import Optional, List

load_dotenv()
logger = logging.getLogger(__name__)

MAX_RESUME_CHARS = 10_000
CHUNK_OVERLAP    = 200   # characters of overlap between chunks


#Output model 
class ResumeData(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    education: List[Education] = []
    experience: List[Experience] = []
    skills: List[str] = []


#Helpers 
def _strip_fences(text: str) -> str:
    """Remove ```json ... ``` wrappers that some models emit."""
    text = text.strip()
    if "```" in text:
        match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
        if match:
            return match.group(1).strip()
    return text


def _parse_json(raw: str) -> Optional[dict]:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("LLM returned invalid JSON")
        return None


def _to_resume_data(data: dict) -> ResumeData:
    try:
        return ResumeData(**data)
    except ValidationError:
        logger.warning("LLM JSON failed schema validation")
        return ResumeData()


def _merge_chunks(results: List[ResumeData]) -> ResumeData:
    """
    Combine multiple chunk results into one ResumeData.
    - Scalars (name/email/phone): first non-null wins.
    - Lists (education/experience/skills): union, de-duplicated by string repr.
    """
    merged = ResumeData()
    seen_edu:  set[str] = set()
    seen_exp:  set[str] = set()
    seen_skl:  set[str] = set()

    for r in results:
        if not merged.name  and r.name:  merged.name  = r.name
        if not merged.email and r.email: merged.email = r.email
        if not merged.phone and r.phone: merged.phone = r.phone

        for e in r.education:
            key = f"{e.degree}|{e.school}"
            if key not in seen_edu:
                seen_edu.add(key)
                merged.education.append(e)

        for x in r.experience:
            key = f"{x.company}|{x.role}"
            if key not in seen_exp:
                seen_exp.add(key)
                merged.experience.append(x)

        for s in r.skills:
            k = s.lower().strip()
            if k and k not in seen_skl:
                seen_skl.add(k)
                merged.skills.append(s)

    return merged


#LLMParser ───
class LLMParser:
    def __init__(self, api_key: str, model: str = "llama-3.1-8b-instant"):
        self.client = Groq(api_key=api_key)
        self.model  = model

    #public ─
    def parse_with_llm(self, resume_text: str) -> ResumeData:
        """
        Parse resume using LLM.
        - Short resumes (≤ MAX_RESUME_CHARS): single call.
        - Long resumes (> MAX_RESUME_CHARS): split into overlapping chunks,
          parse each, then merge sub-results.
        Returns valid ResumeData, or empty ResumeData on any failure.
        """
        if len(resume_text) <= MAX_RESUME_CHARS:
            return self._parse_chunk(resume_text)

        # --- chunked path ---
        chunks  = self._split_chunks(resume_text)
        results = [self._parse_chunk(c) for c in chunks]
        return _merge_chunks(results)

    #private 
    def _split_chunks(self, text: str) -> List[str]:
        """
        Slide a window of MAX_RESUME_CHARS across the text with CHUNK_OVERLAP
        characters of overlap so entries that straddle a boundary are captured.
        """
        chunks: List[str] = []
        step   = MAX_RESUME_CHARS - CHUNK_OVERLAP
        start  = 0
        while start < len(text):
            end = start + MAX_RESUME_CHARS
            chunks.append(text[start:end])
            if end >= len(text):
                break
            start += step
        return chunks

    def _parse_chunk(self, chunk: str) -> ResumeData:
        """Call the LLM for a single text chunk and return ResumeData."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=0,
                max_tokens=2048,
                messages=[
                    {"role": "system", "content": self._build_prompt()},
                    {"role": "user",   "content": chunk},
                ],
            )
            raw = response.choices[0].message.content or ""
        except Exception:
            logger.exception("Groq API error")
            return ResumeData()

        clean = _strip_fences(raw)
        data  = _parse_json(clean)
        if data is None:
            return ResumeData()
        return _to_resume_data(data)

    @staticmethod
    def _build_prompt() -> str:
        return """\
You are an expert resume parser. Extract all information and return ONLY valid JSON.

Schema:
{
  "name": string,
  "email": string,
  "phone": string,
  "education": [{"degree": string, "school": string, "start_date": string, "end_date": string}],
  "experience": [{"company": string, "role": string, "start_date": string, "end_date": string, "description": string}],
  "skills": [string]
}

Rules:
- Return ONLY the JSON object, no explanation or markdown
- Extract dates as "YYYY-MM" format
- If a date is incomplete or missing, use null
- Return empty arrays [] if a section has no data
- If a field value is unknown, use null"""

    #JD skill extraction

    def extract_jd_skills(self, jd_text: str) -> List[str]:
        """
        Extract required skills from a job description using the LLM.

        Returns a list of normalised skill strings, e.g.:
          ["Python", "FastAPI", "Machine Learning", "AWS", "Docker"]

        Falls back to [] on any failure.
        """
        truncated = jd_text[:MAX_RESUME_CHARS]
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=0,
                max_tokens=1024,
                messages=[
                    {"role": "system", "content": self._jd_prompt()},
                    {"role": "user",   "content": truncated},
                ],
            )
            raw = response.choices[0].message.content or ""
        except Exception:
            logger.exception("Groq API error during JD skill extraction")
            return []

        clean = _strip_fences(raw)
        try:
            data = json.loads(clean)
        except json.JSONDecodeError:
            logger.warning("JD skill extraction: LLM returned invalid JSON")
            return []

        # Accept both {"skills": [...]} and a bare list [...]
        if isinstance(data, list):
            skills = data
        elif isinstance(data, dict):
            skills = data.get("skills") or data.get("required_skills") or []
        else:
            return []

        return [s.strip() for s in skills if isinstance(s, str) and s.strip()]

    @staticmethod
    def _jd_prompt() -> str:
        return """\
You are an expert technical recruiter. Extract ALL required skills, technologies, \
programming languages, frameworks, libraries, tools, platforms, and certifications \
from the job description below.

Return ONLY a JSON array of skill strings. Example:
["Python", "FastAPI", "PostgreSQL", "Docker", "AWS", "Machine Learning", "REST APIs"]

Rules:
- Expand common abbreviations (e.g. "JS" → "JavaScript", "ML" → "Machine Learning", "k8s" → "Kubernetes")
- Include both hard skills and explicitly listed soft skills
- Do NOT include job titles, company names, or generic phrases like "strong problem-solving"
- Return [] if no skills are found
- Return ONLY the JSON array, nothing else"""