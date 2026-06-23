from groq import Groq
import json
import logging

import os
from dotenv import load_dotenv
from pydantic import BaseModel,ValidationError
from ast_models import Education, Experience
from typing import Optional
from utils import file_extractor

load_dotenv()
logger = logging.getLogger(__name__)

MAX_RESUME_CHARS = 10_00

class ResumeData(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    education: list[Education] = []
    experience: list[Experience] = []
    skills: list[str] = []

# llm_parser.py
class LLMParser:
    def __init__(self, api_key: str, model: str = "llama-3.1-8b-instant"):
        self.client = Groq(api_key=api_key)
        self.model = model

    def parse_with_llm(self, resume_text: str) -> ResumeData:
        """Parser resume usinh LLM
        Return: 
        Valid ResumeData or Empty ResumeData on failure"""

        try: 
            messages = []
            LLM_MAX_TOKENS = 2048
            #messages.append("role":"user","content":self.__build_prompt())
            response = self.client.chat.completions.create(
                model=self.model,
                temperature = 0,
                max_tokens=LLM_MAX_TOKENS,
                messages=[
                    {
                        "role":"system",
                        "content":self._build_prompt()
                    },
                    {
                        "role":"user",
                        "content":resume_text
                    }
                ]
            )
            llm_output =  response.choices[0].message.content
            try:
                data = json.loads(llm_output)
            except json.JSONDecodeError as e:
                logger.exception("Invalid JSON")
                return ResumeData
            try:
                return ResumeData(**data)
            except ValidationError as e:
                logger.exception("Schemaa Validation Error")
        except:
            logger.exception("Groq api error")
            return ResumeData()

    def _build_prompt(self) -> str:
        return """You are an expert resume parser. Extract all information and return ONLY valid JSON.

Schema:
{
  "name": string,
  "email": string,
  "phone": string,
  "education": [{"degree": string, "school": string, "start_date": string, "end_date": string}],
  "experience": [{"company": string, "role": string, "start_date": string, "end_date": string}],
  "skills": [string]
}

Rules:
- Extract dates as "YYYY-MM" format
- If date is incomplete, use null
- Return empty arrays if no data found"""



txt = file_extractor.extract_text("resumes/resume.pdf",".pdf")
parser  = LLMParser(api_key= os.getenv("GROQ_API_KEY"),model=os.getenv("LLM_MODEL"))
parser.parse_with_llm(txt)