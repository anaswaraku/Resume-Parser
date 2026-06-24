from groq import Groq
import json
import logging
import re
import os
 
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError
from ast_models import Education, Experience
from typing import Optional
 
load_dotenv()
logger = logging.getLogger(__name__)
 
# Bug 1 fix: 10_00 → 10_000  (was 1000, needs to be 10000)
MAX_RESUME_CHARS = 10_000
 
 
class ResumeData(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    education: list[Education] = []
    experience: list[Experience] = []
    skills: list[str] = []
 
 
class LLMParser:
    def __init__(self, api_key: str, model: str = "llama-3.1-8b-instant"):
        self.client = Groq(api_key=api_key)
        self.model = model
 
    def parse_with_llm(self, resume_text: str) -> ResumeData:
        """Parse resume using LLM.
        Returns valid ResumeData, or empty ResumeData on any failure."""
 
        # Bug 2 fix: actually truncate to the token budget
        truncated = resume_text[:MAX_RESUME_CHARS]
 
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=0,
                max_tokens=2048,
                messages=[
                    {"role": "system", "content": self._build_prompt()},
                    {"role": "user",   "content": truncated},
                ]
            )
            llm_output = response.choices[0].message.content
 
            # Strip Markdown code fences if present (some models wrap JSON in ```json ... ```)
            content = llm_output.strip() if llm_output else ""
            if "```" in content:
                match = re.search(r"```(?:json)?\s*(.*?)\s*```", content, re.DOTALL)
                if match:
                    content = match.group(1).strip()
 
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                logger.exception("LLM returned invalid JSON")
                return ResumeData()
 
            try:
                return ResumeData(**data)
            except ValidationError:
                logger.exception("LLM JSON failed schema validation")
                return ResumeData()
 
        except Exception:
            logger.exception("Groq API error")
            return ResumeData()
 
    # Bug 3 fix: spec says _build_prompt(self, resume_text) but text correctly
    # goes in the user message, not the system prompt. Keeping it as a no-arg
    # method and passing text via the user message is the right pattern.
    def _build_prompt(self) -> str:
        return """You are an expert resume parser. Extract all information and return ONLY valid JSON.
 
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
 
from groq import Groq
import json
import logging
import re
import os
 
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError
from ast_models import Education, Experience
from typing import Optional
 
load_dotenv()
logger = logging.getLogger(__name__)
 
# Bug 1 fix: 10_00 → 10_000  (was 1000, needs to be 10000)
MAX_RESUME_CHARS = 10_000
 
 
class ResumeData(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    education: list[Education] = []
    experience: list[Experience] = []
    skills: list[str] = []
 
 
class LLMParser:
    def __init__(self, api_key: str, model: str = "llama-3.1-8b-instant"):
        self.client = Groq(api_key=api_key)
        self.model = model
 
    def parse_with_llm(self, resume_text: str) -> ResumeData:
        """Parse resume using LLM.
        Returns valid ResumeData, or empty ResumeData on any failure."""
 
        # Bug 2 fix: actually truncate to the token budget
        truncated = resume_text[:MAX_RESUME_CHARS]
 
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=0,
                max_tokens=2048,
                messages=[
                    {"role": "system", "content": self._build_prompt()},
                    {"role": "user",   "content": truncated},
                ]
            )
            llm_output = response.choices[0].message.content
 
            # Strip Markdown code fences if present (some models wrap JSON in ```json ... ```)
            content = llm_output.strip() if llm_output else ""
            if "```" in content:
                match = re.search(r"```(?:json)?\s*(.*?)\s*```", content, re.DOTALL)
                if match:
                    content = match.group(1).strip()
 
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                logger.exception("LLM returned invalid JSON")
                return ResumeData()
 
            try:
                return ResumeData(**data)
            except ValidationError:
                logger.exception("LLM JSON failed schema validation")
                return ResumeData()
 
        except Exception:
            logger.exception("Groq API error")
            return ResumeData()
 
    def _build_prompt(self) -> str:
        return """You are an expert resume parser. Extract all information and return ONLY valid JSON.
 
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
 