"""
Syntactic Analysis (Top-Down / Recursive Descent Parser).

The hierarchy:
    ResumeAST                        ← root node
    ├── name, email, phone           ← contact fields (leaf nodes)
    ├── education: List[Education]   ← section node → entry nodes
    │     └── Education              ← entry node → degree, school, dates (leaves)
    ├── experience: List[Experience] ← section node → entry nodes
    │     └── Experience             ← entry node → company, role, dates, desc
    └── skills: List[str]            ← section node → leaf list

step1: Token[] -> Line[]
step2: Line[]->Section[]
step3: Section("eduction")->EducationNode[]
step4: ResumeNode -> ResumeAST 
"""
from __future__ import annotations
from typing import List,Optional,Tuple
from lexer import Token
from dataclasses import dataclass
from collections import defaultdict
from ast_models import Education, Experience
@dataclass
class Line:
    type:str
    value:List[str] 
 
from dataclasses import dataclass, field
from typing import List
 
 
@dataclass
class Token:
    type: str
    value: str
    position: int
 
def __repr__(self) -> str:  
    return f"Token({self.type}, {self.value!r})"
 
 
@dataclass
class Line:
    tokens: List[Token]
    raw: str                  # space-joined values of non-NEWLINE tokens
    line_number: int          # 1-based, useful for debug / ParseIssue reporting
 
# ── convenience helpers used by SectionDetector & section parsers ─────────  
    def is_blank(self) -> bool:  
        """True for the empty lines that represent blank separators."""  
        return len(self.tokens) == 0  
    
    def has_type(self, ttype: str) -> bool:  
        return any(t.type == ttype for t in self.tokens)  
    
    def token_types(self) -> List[str]:  
        return [t.type for t in self.tokens]  
    
    def word_count(self) -> int:  
        return sum(1 for t in self.tokens if t.type == "WORD")  
    
    def text_lower(self) -> str:  
        return self.raw.strip().lower()  
    
    def __repr__(self) -> str:  
        if self.is_blank():  
            return f"Line({self.line_number}, <blank>)"  
        return f"Line({self.line_number}, {self.raw!r})"
 
class LineBuilder: 
    def build(self, tokens: List[Token]) -> List[Line]:  
        lines: List[Line] = []  
        current: List[Token] = []  
        line_number = 1  
    
        for token in tokens:  
            if token.type == "NEWLINE":  
                # Always flush — even an empty buffer becomes a blank Line  
                lines.append(self._make_line(current, line_number))  
                current = []  
                line_number += 1  
            else:  
                current.append(token)  
    
        # Trailing content with no final newline  
        if current:  
            lines.append(self._make_line(current, line_number))  
    
        return lines  
 
    
    @staticmethod  
    def _make_line(tokens: List[Token], line_number: int) -> Line:  
        raw = " ".join(t.value for t in tokens)   # blank line → raw=""  
        return Line(tokens=tokens, raw=raw, line_number=line_number)
  
class Normalizer:
    import re
    RULES: List[Tuple[re.Pattern, str]] = [
        (re.compile(r'\bb\.?\s*tech\.?\b',            re.I), "Bachelor of Technology"),
        (re.compile(r'\bb\.?\s*e\.?\b',               re.I), "Bachelor of Engineering"), 
        (re.compile(r'\bb\.?\s*sc\.?\b',              re.I), "Bachelor of Science"),    
        (re.compile(r'\bb\.?\s*com\.?\b',             re.I), "Bachelor of Commerce"),    
        (re.compile(r'\bb\.?\s*a\.?\b',               re.I), "Bachelor of Arts"),    
        (re.compile(r'\bm\.?\s*tech\.?\b',            re.I), "Master of Technology"),    
        (re.compile(r'\bm\.?\s*e\.?\b',               re.I), "Master of Engineering"),    
        (re.compile(r'\bm\.?\s*sc\.?\b',              re.I), "Master of Science"),    
        (re.compile(r'\bm\.?\s*b\.?\s*a\.?\b',       re.I), "Master of Business Administration"),
        (re.compile(r'\bph\.?\s*d\.?\b',              re.I), "PhD"),        
        # "Sept" is the only common non-standard abbreviation    
        (re.compile(r'\bsept\b',                      re.I), "Sep"),     
        (re.compile(r'\b(present|current|now|ongoing|till\s+date|to\s+date)\b', re.I), "Present"),  
        (re.compile(r'^[\s•·▪▸\-–—*]+'),              ""),   
        (re.compile(r'\bwork\s+history\b',            re.I), "experience"),    
        (re.compile(r'\bprofessional\s+experience\b', re.I), "experience"),    
        (re.compile(r'\bwork\s+experience\b',         re.I), "experience"),    
        (re.compile(r'\bemployment\s+history\b',      re.I), "experience"),    
        (re.compile(r'\bacademic\s+background\b',     re.I), "education"),    
        (re.compile(r'\beducational\s+qualification', re.I), "education"),    
        (re.compile(r'\btechnical\s+skills\b',        re.I), "skills"),    
        (re.compile(r'\bcore\s+competencies\b',       re.I), "skills"),    
        (re.compile(r'\bkey\s+skills\b',              re.I), "skills"),    
    ]
 
 

    def normalize(self, lines: List[Line]) -> List[Line]:
        return [self._normalize_line(line) for line in lines]
 
    def _normalize_line(self, line: "Line") -> "Line":    
        if line.is_blank():    
            return line                  # nothing to normalise on a blank line   
        raw = line.raw    
        changed = False   
      
        for pattern, replacement in self.RULES:    
            new_raw, n = pattern.subn(replacement, raw)    
            if n:    
                raw = new_raw.strip()   # strip any edge whitespace left behind    
                changed = True    
                # don't break — multiple rules can apply to one line       
        if not changed:    
            return line                  # reuse original object, no allocation    
    
        # Return a new Line with normalised raw but original tokens intact.
    
        # Tokens are the lexer's ground truth; raw is for text-level matching.
        #  # adjust import to your package layout
    
        return Line(
            tokens=line.tokens,
            raw=raw,
            line_number=line.line_number,
        )
 
class HeaderBuilder:
    SECTION_KW = {
        "Summary":["Summary", "Career Objective", "Professional Summary","Objective"],
        "Education":["Education","Academic Details","Academic Background","Qualifications"," Academic History",],
        "Technical Skills":["Technical Skills","Skills","Tech Stack","Core Competencies","Coding Skills", "Development Skills"],
        "Experience":["Experience","Work Experience"," Internships", "Professional","Experience","Career", "Job","Internships"],
        "Certifications":["Certifications","Licenses","Courses"],
        "Leadership":[ "Leadership","Leadership Experience","Roles & Responsibilities"],
        "Extra-Curricular Activities":[
            "Extra-Curricular Activities","Activities","Interests"
        ],
        "Publications":["Research Papers","Research","Papers"],
    }

    def find_header(self, lines):
        n = Normalizer()
        l=[]
        for line in lines:
            l.append(n._normalize_line(line=line))
        return l    
        
            

    
class SectionBuilder:
    """Converts lines to section"""
    def build(self,lines:List):
        return lines
    
class ResumeParser:
    def build(self, tokens:List[Token]):
        lines = LineBuilder().build(tokens=tokens)
        sections =HeaderBuilder().find_header(lines=lines)
        return sections