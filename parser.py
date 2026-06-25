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
from typing import List,Optional,Tuple,Set,Dict
from lexer import Token
from dataclasses import dataclass
from collections import defaultdict
from ast_models import Education, Experience,ResumeAST
@dataclass
class Line:
    type:str
    value:List[str] 

from dataclasses import dataclass, field
from typing import List


@dataclass
class ParseContext:
    section_headers: Set[str] = field(
        default_factory=lambda: {
            "education",
            "experience",
            "skills",
            "projects",
            "certifications",
            "awards",
            "publications",
            "languages",
            "summary",
            "objective",
        }
    )
    degree_keywords: Set[str] = field(
        default_factory=lambda: {
            "bachelor",
            "master",
            "phd",
            "doctorate",
            "diploma",
            "associate",
            "bachelor of technology",
            "master of technology",
            "bachelor of science",
            "master of science",
            "bachelor of engineering",
            "master of engineering",
            "bachelor of arts",
            "master of business administration",
        }
    )
    school_keywords: Set[str] = field(
        default_factory=lambda: {
            "university",
            "college",
            "institute",
            "institution",
            "school",
            "academy",
            "iit",
            "nit",
            "iim",
        }
    )
    company_suffixes: Set[str] = field(
        default_factory=lambda: {
            "inc",
            "ltd",
            "llc",
            "pvt",
            "corp",
            "co",
            "technologies",
            "solutions",
            "systems",
            "services",
        }
    )
    role_keywords: Set[str] = field(
        default_factory=lambda: {
            "engineer",
            "developer",
            "analyst",
            "manager",
            "designer",
            "architect",
            "consultant",
            "intern",
            "lead",
            "head",
            "officer",
            "director",
            "associate",
            "specialist",
        }
    )


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
 
#convenience helpers used by SectionBuilder & section parsers   
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

    def all_word_types(self) -> bool:
        """True when every token is a WORD (typical for a name line)."""
        return bool(self.tokens) and all(t.type == "WORD" for t in self.tokens)
    
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

#Block helper (shared by Education and Experience) 

def split_into_blocks(lines: List[Line]) -> List[List[Line]]:
    """Split a section's lines into entry blocks on blank lines."""
    blocks: List[List[Line]] = []
    current: List[Line] = []
    for line in lines:
        if line.is_blank():
            if current:
                blocks.append(current)
                current = []
        else:
            current.append(line)
    if current:
        blocks.append(current)
    return blocks


#ParsedField 

@dataclass
class ParsedField:
    value: Optional[str]
    confidence: float = 0.0


#ParseIssue 

@dataclass
class ParseIssue:
    section: str
    message: str
    line_number: Optional[int] = None
    severity: str = "warning"


#EducationNode (internal) 

@dataclass
class EducationNode:
    degree:     ParsedField = field(default_factory=lambda: ParsedField(None))
    school:     ParsedField = field(default_factory=lambda: ParsedField(None))
    start_date: ParsedField = field(default_factory=lambda: ParsedField(None))
    end_date:   ParsedField = field(default_factory=lambda: ParsedField(None))


#EducationParser 

class EducationParser:
    """
     Education section parsing.

    Receives Section("education") and returns List[EducationNode].

    Strategy
    ────────
    1. Split section lines into blank-line-delimited blocks.
       Each block = one education entry.
    2. For each line in a block, score it against three classifiers:
         _score_degree()    — contains degree keyword?
         _score_school()    — contains school keyword?
         _score_date_range()— contains DATE tokens?
    3. Assign the line to whichever field has the highest score.
       Ties: date_range wins (most unambiguous), then degree, then school.
    4. Missing fields → ParsedField(None, 0.0); Pydantic handles Optional.
    """

    def __init__(self, context: ParseContext) -> None:
        self.ctx = context
        self.issues: List[ParseIssue] = []

    def parse(self, section: Optional[Section]) -> List[Education]:
        if section is None:
            return []
        nodes = [self._parse_block(block)
                 for block in split_into_blocks(section.lines)]
        # Filter blocks that yielded nothing useful
        nodes = [n for n in nodes if n.degree.value or n.school.value]
        return [self._to_model(n) for n in nodes]

    #block parser ────────

    def _parse_block(self, block: List[Line]) -> EducationNode:
        node = EducationNode()

        for line in block:
            d  = self._score_degree(line)
            s  = self._score_school(line)
            dt = self._score_date_range(line)

            # Date range is the most unambiguous — assign first
            if dt >= 0.9:
                dates = self._extract_dates(line)
                node.start_date = ParsedField(dates[0], dt)
                node.end_date   = ParsedField(dates[1] if len(dates) > 1 else None, dt)

            # Degree vs school — only if date didn't win
            elif d >= s and d > 0.3 and node.degree.value is None:
                node.degree = ParsedField(line.raw.strip(), d)

            elif s > d and s > 0.3 and node.school.value is None:
                node.school = ParsedField(line.raw.strip(), s)

            # Low-confidence fallback: first short line → degree, second → school
            elif node.degree.value is None and line.word_count() <= 7:
                node.degree = ParsedField(line.raw.strip(), 0.2)

            elif node.school.value is None and line.word_count() <= 6:
                node.school = ParsedField(line.raw.strip(), 0.2)

        if node.degree.value is None:
            self.issues.append(ParseIssue(
                section="education",
                message="Could not identify degree in block",
                line_number=block[0].line_number if block else None,
            ))

        return node

    #scoring ────

    def _score_degree(self, line: Line) -> float:
        text  = line.text_lower()
        score = 0.0
        if any(kw in text for kw in self.ctx.degree_keywords):
            score += 0.8
        if line.word_count() <= 8:
            score += 0.1
        if line.has_type("DATE"):           # dates don't belong in a degree line
            score -= 0.6
        if line.has_type("EMAIL"):
            score -= 0.9
        return max(0.0, min(score, 1.0))

    def _score_school(self, line: Line) -> float:
        text  = line.text_lower()
        score = 0.0
        if any(kw in text for kw in self.ctx.school_keywords):
            score += 0.75
        if 2 <= line.word_count() <= 6:
            score += 0.1
        if line.has_type("DATE"):
            score -= 0.5
        return max(0.0, min(score, 1.0))

    def _score_date_range(self, line: Line) -> float:
        date_count = sum(1 for t in line.tokens if t.type == "DATE")
        if date_count >= 2:
            return 0.95     # "Sep 2018 – May 2022" — very high confidence
        if date_count == 1:
            return 0.80     # single date or "Sep 2018 – Present"
        return 0.0

    #date extraction ─────

    @staticmethod
    def _extract_dates(line: Line) -> List[str]:
        """Return [start, end] or [start] from DATE tokens on the line."""
        return [t.value for t in line.tokens if t.type == "DATE"]

    #internal → Pydantic ─

    @staticmethod
    def _to_model(node: EducationNode) -> Education:
        return Education(
            degree=node.degree.value     or "",
            school=node.school.value     or "",
            start_date=node.start_date.value,
            end_date=node.end_date.value,
        )
#ExperienceNode (internal) ─

@dataclass
class ExperienceNode:
    company:    ParsedField       = field(default_factory=lambda: ParsedField(None))
    role:       ParsedField       = field(default_factory=lambda: ParsedField(None))
    start_date: ParsedField       = field(default_factory=lambda: ParsedField(None))
    end_date:   ParsedField       = field(default_factory=lambda: ParsedField(None))
    description: List[str]        = field(default_factory=list)


#ExperienceParser ────────

class ExperienceParser:
    """
    Stage 6b — Experience section parsing.

    Line classification priority (highest confidence first):
      1. DATE line     → start_date / end_date
      2. DESCRIPTION   → token_count > 8, or starts with action verb
      3. ROLE line     → contains role keyword (Engineer, Manager …)
      4. COMPANY line  → contains company suffix or is short title-case line
      5. FALLBACK      → first unassigned short line → company,
                         second → role
    """

    # Common CV action verbs — strong signal for description lines
    _ACTION_VERBS: Set[str] = {
        "built", "developed", "designed", "implemented", "led", "managed",
        "created", "maintained", "improved", "optimised", "optimized",
        "reduced", "increased", "delivered", "deployed", "integrated",
        "collaborated", "worked", "wrote", "migrated", "refactored",
        "automated", "tested", "reviewed", "mentored", "analysed", "analyzed",
    }

    def __init__(self, context: ParseContext) -> None:
        self.ctx = context
        self.issues: List[ParseIssue] = []

    def parse(self, section: Optional[Section]) -> List[Experience]:
        if section is None:
            return []
        nodes = [self._parse_block(block)
                 for block in split_into_blocks(section.lines)]
        nodes = [n for n in nodes if n.company.value or n.role.value]
        return [self._to_model(n) for n in nodes]

    #block parser ────────

    def _parse_block(self, block: List[Line]) -> ExperienceNode:
        node = ExperienceNode()

        for line in block:
            # 1 — Date range (most unambiguous)
            if self._score_date_range(line) >= 0.8:
                dates = [t.value for t in line.tokens if t.type == "DATE"]
                node.start_date = ParsedField(dates[0], 0.95)
                node.end_date   = ParsedField(dates[1] if len(dates) > 1 else None, 0.95)
                continue

            # 2 — Description line
            if self._is_description(line):
                node.description.append(line.raw.strip())
                continue

            # 3 — Role line
            role_score = self._score_role(line)
            if role_score > 0.5 and node.role.value is None:
                node.role = ParsedField(line.raw.strip(), role_score)
                continue

            # 4 — Company line
            company_score = self._score_company(line)
            if company_score > 0.4 and node.company.value is None:
                node.company = ParsedField(line.raw.strip(), company_score)
                continue

            # 5 — Fallback: short lines fill company then role
            if node.company.value is None and line.word_count() <= 5:
                node.company = ParsedField(line.raw.strip(), 0.2)
            elif node.role.value is None and line.word_count() <= 6:
                node.role = ParsedField(line.raw.strip(), 0.2)

        if node.company.value is None and node.role.value is None:
            self.issues.append(ParseIssue(
                section="experience",
                message="Could not identify company or role in block",
                line_number=block[0].line_number if block else None,
            ))

        return node

    #classifiers (section-specific — no global LineType enum) ────

    def _is_description(self, line: Line) -> bool:
        """High token count or starts with a known action verb."""
        if len(line.tokens) > 8:
            return True
        first_word = line.tokens[0].value.lower() if line.tokens else ""
        return first_word in self._ACTION_VERBS

    def _score_date_range(self, line: Line) -> float:
        date_count = sum(1 for t in line.tokens if t.type == "DATE")
        if date_count >= 2:
            return 0.95
        if date_count == 1:
            return 0.80
        return 0.0

    def _score_role(self, line: Line) -> float:
        text  = line.text_lower()
        score = 0.0
        if any(kw in text for kw in self.ctx.role_keywords):
            score += 0.7
        if line.word_count() <= 5:
            score += 0.1
        if line.has_type("DATE"):
            score -= 0.5
        return max(0.0, min(score, 1.0))

    def _score_company(self, line: Line) -> float:
        text  = line.text_lower()
        score = 0.0
        if any(sfx in text for sfx in self.ctx.company_suffixes):
            score += 0.7
        # Title-case short line — likely a proper noun (company name)
        if line.raw.istitle() and line.word_count() <= 4:
            score += 0.4
        if line.has_type("DATE"):
            score -= 0.5
        return max(0.0, min(score, 1.0))

    #internal → Pydantic ─

    @staticmethod
    def _to_model(node: ExperienceNode) -> Experience:
        desc = " ".join(node.description) if node.description else None
        return Experience(
            company=node.company.value    or "",
            role=node.role.value          or "",
            start_date=node.start_date.value,
            end_date=node.end_date.value,
            description=desc,
        )


@dataclass
class HeaderNode:
    name:  Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    urls:  List[str]     = field(default_factory=list)

class SkillsParser:
    """
    Stage 6c — Skills section parsing.

    Two formats handled:
      - Separator-delimited  →  "Python, Django, REST APIs"
      - One-per-line         →  each non-blank line is a skill
    Multi-word skills (e.g. "Machine Learning") are preserved.
    """

    _STRIP_CHARS = ",.·•*▪▸-–— \t"

    def parse(self, section: Optional[Section]) -> List[str]:
        if section is None:
            return []

        skills: List[str] = []
        for line in section.lines:
            if line.is_blank():
                continue

            # If line has SEPARATOR tokens, split on them
            if line.has_type("SEPARATOR"):
                skills.extend(self._split_on_separators(line))
            else:
                # Whole line is one skill (e.g. "Machine Learning")
                skill = line.raw.strip(self._STRIP_CHARS)
                if skill:
                    skills.append(skill)

        # Deduplicate while preserving order
        seen: Set[str] = set()
        result: List[str] = []
        for s in skills:
            key = s.lower()
            if key not in seen:
                seen.add(key)
                result.append(s)
        return result

    def _split_on_separators(self, line: Line) -> List[str]:
        """
        Group tokens between SEPARATOR tokens into skill strings.
        Consecutive WORDs form a single multi-word skill.
        """
        skills, current_words = [], []
        for token in line.tokens:
            if token.type == "SEPARATOR":
                if current_words:
                    skills.append(" ".join(current_words))
                    current_words = []
            else:
                val = token.value.strip(self._STRIP_CHARS)
                if val:
                    current_words.append(val)
        if current_words:
            skills.append(" ".join(current_words))
        return [s for s in skills if s]

class HeaderBuilder:
    def __init__(self, context: ParseContext) -> None:
        self.ctx = context

    def parse(self, lines: List[Line]) -> Tuple[HeaderNode, List[Line]]:
        header_lines: List[Line] = []
        remaining:    List[Line] = []

        # Split at the first section header line
        hit_section = False
        for line in lines:
            if not hit_section and self._is_section_header(line):
                hit_section = True
            if hit_section:
                remaining.append(line)
            else:
                header_lines.append(line)

        node = self._extract(header_lines)
        return node, remaining

    # private helper methods
    def _is_section_header(self, line: Line) -> bool:
        return line.text_lower() in self.ctx.section_headers

    def _extract(self, lines: List[Line]) -> HeaderNode:
        node = HeaderNode()

        for line in lines:
            if line.is_blank():
                continue

            # Email — token-level (most reliable)
            if not node.email and line.has_type("EMAIL"):
                node.email = self._first_of_type(line, "EMAIL")

            # Phone — token-level
            if not node.phone and line.has_type("PHONE"):
                node.phone = self._first_of_type(line, "PHONE")

            # URL — token-level
            if line.has_type("URL"):
                node.urls.append(self._first_of_type(line, "URL"))

            # Name — heuristic: first non-blank line with only WORDs,
            # 2-4 tokens, no special types already claimed above
            if (
                node.name is None
                and line.all_word_types()
                and 2 <= line.word_count() <= 5
                and not line.has_type("EMAIL")
                and not line.has_type("PHONE")
                and not line.has_type("URL")
            ):
                node.name = line.raw.strip()

        return node

    @staticmethod
    def _first_of_type(line: Line, ttype: str) -> str:
        return next(t.value for t in line.tokens if t.type == ttype)


@dataclass
class Section:
    name: str
    lines: List[Line]
    confidence: float = 1.0  # 1.0 = exact match, <1.0 = alias/fuzzy match

    def __repr__(self) -> str:
        return f"Section({self.name!r}, conf={self.confidence:.2f}, lines={len(self.lines)})"


class SectionBuilder:
    _ALIASES: Dict[str, str] = {
        "work history":               "experience",
        "professional experience":    "experience",
        "work experience":            "experience",
        "employment history":         "experience",
        "career history":             "experience",
        "academic background":        "education",
        "educational qualification":  "education",
        "educational qualifications": "education",
        "academic qualifications":    "education",
        "technical skills":           "skills",
        "core competencies":          "skills",
        "key skills":                 "skills",
        "areas of expertise":         "skills",
        "professional skills":        "skills",
        "projects":                   "projects",
        "personal projects":          "projects",
        "certifications":             "certifications",
        "certificates":               "certifications",
        "awards":                     "awards",
        "honours":                    "awards",
        "honors":                     "awards",
        "publications":               "publications",
        "languages":                  "languages",
        "summary":                    "summary",
        "professional summary":       "summary",
        "objective":                  "summary",
        "career objective":           "summary",
        "about me":                   "summary",
    }

    def __init__(self, context: ParseContext) -> None:
        self.ctx = context

    def detect(self, lines: List[Line]) -> List[Section]:
        """
        Walk lines.  On each header line start a new Section.
        Lines before the very first header are collected under an
        "unknown" section (should be rare after HeaderBuilder runs).
        """
        sections:      List[Section]  = []
        current_name:  str            = "unknown"
        current_conf:  float          = 1.0
        current_lines: List[Line]     = []

        for line in lines:
            result = self._classify_header(line)
            if result is not None:
                # Flush whatever was accumulated
                if current_lines or current_name != "unknown":
                    sections.append(Section(
                        name=current_name,
                        lines=current_lines,
                        confidence=current_conf,
                    ))
                current_name  = result[0]
                current_conf  = result[1]
                current_lines = []          # header line itself not included
            else:
                current_lines.append(line)

        # Flush the last section
        if current_lines:
            sections.append(Section(
                name=current_name,
                lines=current_lines,
                confidence=current_conf,
            ))

        return sections

    def as_dict(self, sections: List[Section]) -> Dict[str, Section]:
        """
        Convenience: keyed by canonical section name.
        If the same canonical name appears twice the higher-confidence
        one wins (unusual but possible with badly formatted resumes).
        """
        result: Dict[str, Section] = {}
        for s in sections:
            if s.name not in result or s.confidence > result[s.name].confidence:
                result[s.name] = s
        return result

    #private ────

    def _classify_header(self, line: Line) -> Optional[Tuple[str, float]]:
        """
        Returns (canonical_name, confidence) if line is a section header,
        else None.
        """
        if line.is_blank():
            return None

        text = line.text_lower()

        # 1 — Exact match against canonical set
        if text in self.ctx.section_headers:
            return text, 1.0

        # 2 — Alias table
        if text in self._ALIASES:
            return self._ALIASES[text], 0.85

        # 3 — Substring: any canonical header contained in the line text
        #     Guards against "MY EDUCATION" or "EDUCATION & TRAINING"
        for canonical in self.ctx.section_headers:
            if canonical in text and line.word_count() <= 4:
                return canonical, 0.70

        return None

class ResumeParser:
    def __init__(self, context: Optional[ParseContext] = None) -> None:
        self.ctx = context or ParseContext()

    def build(self, tokens: List[Token]) -> ResumeAST:
        lines   = LineBuilder().build(tokens)
        lines   = Normalizer().normalize(lines)
        header, remaining = HeaderBuilder(self.ctx).parse(lines)

        sb      = SectionBuilder(self.ctx)
        sec_map = sb.as_dict(sb.detect(remaining))

        return ResumeAST(
            name=header.name,
            email=header.email,
            phone=header.phone,
            education=EducationParser(self.ctx).parse(sec_map.get("education")),
            experience=ExperienceParser(self.ctx).parse(sec_map.get("experience")),
            skills=SkillsParser().parse(sec_map.get("skills")),
        )