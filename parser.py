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
from typing import List,Optional
from lexer import Token
from dataclasses import dataclass
from collections import defaultdict
    
@dataclass
class Line:
    type:str
    value:List[str]

class LineBuilder:
    def build(self, tokens: List[Token]):
        lines = []
        current_tokens = []
        grouped_data=defaultdict(list)
        for token in tokens:
            group_key = token["type"]
            if token.type!="NEWLINE":
                current_tokens.append(token.value)
            else:
                for token 
                grouped_data[group_key]
                lines.append(current_tokens)
                current_tokens=[]
        return lines
    
section_kw=["Summary","Education","Experience","Professional Summary","Skills","Technical Skills","Achievements","Certificates","WorkExperience","Objective","Projects","Awards"]   

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

    
    def find_header(self, lines: List[List[str]]) -> List[List[str]]:
        import re
        # Precompile all patterns once
        compiled_patterns = {
            canonical: re.compile(
                r"\b(?:{})\b".format("|".join(re.escape(alias) for alias in aliases)),
                flags=re.IGNORECASE
            )
            for canonical, aliases in self.SECTION_KW.items()
        }

        # Iterate through rows and columns
        for i in range(len(lines)):
            for j in range(len(lines[i])):
                cell = lines[i][j]
                if not isinstance(cell, str):
                    continue

                for canonical_word, pattern in compiled_patterns.items():
                    cell = pattern.sub(canonical_word, cell)

                lines[i][j] = cell

        return lines

    
class SectionBuilder:
    """Converts lines to section"""
    def build(self,lines:List):
        section = []
        current_lines=[]
        for line in lines:#each list element
            for i in range(len(line)):#loop through inner list
                if line[i] not in section_kw:
                    current_lines.append(line[i])
                else:
                    section.append(current_lines)
                    current_lines=[]
        return section
    
class ResumeParser:
    def build(self, tokens:List[Token]):
        lines = LineBuilder().build(tokens=tokens)
        #sections = HeaderBuilder().find_header(lines=lines)
        return lines