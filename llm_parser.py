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
                    {"role": "user", "content": truncated},
                ],
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

    def extract_jd_skills_with_llm(self, jd_text: str) -> list[str]:
        """Extract skills from a job description using LLM."""
        truncated = jd_text[:MAX_RESUME_CHARS]
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=0,
                max_tokens=1024,
                messages=[
                    {
                        "role": "system",
                        "content": 'You are an expert technical recruiter. Your task is to extract all key technical skills, frameworks, and tools from the following job description. Focus on concrete technologies and methodologies. Exclude generic soft skills like "communication" or "teamwork". Return ONLY a valid JSON array of strings. For example: ["Python", "AWS", "Docker", "Kubernetes", "CI/CD"]. Do not return anything else.',
                    },
                    {"role": "user", "content": truncated},
                ],
            )
            llm_output = response.choices[0].message.content
            content = llm_output.strip() if llm_output else ""
            if "```" in content:
                match = re.search(r"```(?:json)?\s*(.*?)\s*```", content, re.DOTALL)
                if match:
                    content = match.group(1).strip()
            data = json.loads(content)
            if isinstance(data, list):
                return [str(item) for item in data]
            return []
        except Exception:
            logger.exception("Groq API error while extracting JD skills")
            return []

    def _build_prompt(self) -> str:
        return """You are an expert resume parser. Your task is to extract structured information from the provided resume text and return it as a valid JSON object.
 
Schema:
{
  "name": "string | null",
  "email": "string | null",
  "phone": "string | null",
  "education": [{"degree": "string", "school": "string", "start_date": "string | null", "end_date": "string | null"}],
  "experience": [{"company": "string", "role": "string", "start_date": "string | null", "end_date": "string | null", "description": "string | null"}],
  "skills": ["string"]
}
 
Rules:
- Adhere strictly to the JSON schema. Return ONLY the JSON object, with no additional text, explanations, or markdown fences.
- For the "description" field within each experience entry, preserve the original text, including bullet points and newlines. This is crucial for retaining context.
- Extract dates to the "YYYY-MM" format if possible. If only the year is available, use "YYYY". If a date is ongoing (e.g., "Present"), set the end_date to null. If a date is missing, use null.
- For the "skills" section, extract concrete technical skills, tools, and programming languages. Avoid generic soft skills like "teamwork" or "communication".
- If a top-level field (like "name" or "email") is not found, its value should be null.
- If a section like "education" or "experience" is not found, return an empty array `[]`.
"""
