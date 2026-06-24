from typing import List, Optional
from pydantic import BaseModel, field_validator
import re


class Education(BaseModel):
    degree: Optional[str] = None
    school: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class Experience(BaseModel):
    company: Optional[str] = None
    role: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None


class ResumeAST(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    education: List[Education] = []
    experience: List[Experience] = []
    skills: List[str] = []

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        if v and not re.match(r"[^@]+@[^@]+\.[^@]+", v):
            return None
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v):
        if v:
            digits = re.sub(r"\D", "", v)
            if len(digits) < 10:
                return None
        return v

    @field_validator("skills")
    @classmethod
    def dedupe_skills(cls, v):
        seen, result = set(), []
        for s in v:
            key = s.lower()
            if key not in seen:
                seen.add(key)
                result.append(s)
        return result