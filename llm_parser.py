from groq import Groq
import json
import logging
import re
import os
 
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError
from ast_models import Education, Experience, ResumeAST
from typing import Optional
 
load_dotenv()
logger = logging.getLogger(__name__)
 
MAX_RESUME_CHARS = 10_000
 
 
class LLMParser:
    def __init__(self, api_key: str, model: str = "llama-3.1-8b-instant"):
        self.client = Groq(api_key=api_key)
        self.model = model
 
    def parse_with_llm(self, resume_text: str) -> ResumeAST:
        """Parse resume using LLM.
        Returns valid ResumeAST, or empty ResumeAST on any failure."""
 
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
                return ResumeAST()
 
            try:
                return ResumeAST(**data)
            except ValidationError:
                logger.exception("LLM JSON failed schema validation")
                return ResumeAST()
 
        except Exception:
            logger.exception("Groq API error")
            return ResumeAST()
 
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
 
 