# Pydantic data models
from  pydantic import BaseModel
from typing import List, Optional
# ast.py
class Education(BaseModel):
    degree: Optional[str]=None
    school: Optional[str]=None
    start_date: Optional[str]=None
    end_date: Optional[str]=None

class Experience(BaseModel):
    company: Optional[str]=None
    role: Optional[str]=None
    start_date: Optional[str]=None
    end_date: Optional[str]=None
    description: Optional[str]=None

class ResumeAST(BaseModel):
    name: Optional[str]=None
    email: Optional[str]=None
    phone: Optional[str]=None
    summary: Optional[str]=None
    education: List[Education] = []
    experience: List[Experience] = []
    skills: List[str] = []