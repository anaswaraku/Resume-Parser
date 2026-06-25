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
import re
from typing import List,Optional,Tuple,Set,Dict
from lexer import Token
from dataclasses import dataclass
from collections import defaultdict
from ast_models import Education, Experience,ResumeAST
from dateutil import parser as date_parser
from dataclasses import dataclass, field
from typing import List

DATE_TYPES = {"DATE", "DATE_RANGE", "YEAR_RANGE", "DATE_DMY", "YEAR","PRESENT"}


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
            "PhD"
            "P.hd",
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
            "phd in"
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
            "pvt.",
            "pvt. ltd",
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
        
    def has_date(self) -> bool:
        return any(t.type in DATE_TYPES for t in self.tokens)
        
    def extract_dates(self) -> List[str]:
        """Extract individual dates from all date-like tokens."""

        def normalize_date(d_str:str)->str:
            d_lower = d_str.strip().lower()
            if d_lower in ("present","current","now"):
                return "Present"
            try:
                dt = date_parser.parse(d_str)
                return dt.strftime("%Y-%m")
            except (ValueError,TypeError,OverflowError):
                return d_str.strip()
        dates = []
        for t in self.tokens:
            if t.type in {"DATE_RANGE", "YEAR_RANGE"}:
                parts = re.split(r'\s*[-–—to]+\s*', t.value, maxsplit=1)
                dates.extend([normalize_date(p) for p in parts if p.strip()])
            elif t.type in DATE_TYPES:
                dates.append(normalize_date(t.value))
        return dates

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
        (re.compile(r'\bresearch\s+experience\b',     re.I), "experience"),
        (re.compile(r'\bacademic\s+background\b',     re.I), "education"),    
        (re.compile(r'\beducational\s+qualification', re.I), "education"),
        (re.compile(r'\bacademic\s+details\b',        re.I), "education"),
        (re.compile(r'\beducation\s+&\s+credentials\b',re.I), "education"),
        (re.compile(r'\btechnical\s+skills\b',        re.I), "skills"),    
        (re.compile(r'\bcore\s+competencies\b',       re.I), "skills"),    
        (re.compile(r'\bkey\s+skills\b',              re.I), "skills"),
        (re.compile(r'\bcomputer\s+skills\b',         re.I), "skills"),
        (re.compile(r'\bskill\s+set\b',               re.I), "skills"),    
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
    """Split a section's lines into entry blocks on blank lines or when multiple strong dates are encountered."""
    blocks: List[List[Line]] = []
    current: List[Line] = []
    has_date = False

    def _has_strong_date(line: Line) -> bool:
        date_tokens = [t for t in line.tokens if t.type in {"DATE_RANGE", "YEAR_RANGE", "DATE_DMY", "DATE"}]
        if any(t.type in {"DATE_RANGE", "YEAR_RANGE"} for t in date_tokens):
            return True
        if len(date_tokens) >= 2:
            return True
        return False

    for line in lines:
        if line.is_blank():
            if current:
                blocks.append(current)
                current = []
                has_date = False
        else:
            line_has_date = _has_strong_date(line)
            if line_has_date and has_date:
                blocks.append(current)
                current = [line]
                has_date = True
            else:
                current.append(line)
                if line_has_date:
                    has_date = True

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
    description: List[str]  = field(default_factory=list)


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

        # --- Filter out irrelevant lines ---
        relevant_lines = []
        for line in block:
            l_lower = line.text_lower()
            if not l_lower.startswith(("advisor:", "thesis:", "research:", "{ ranked")):
                relevant_lines.append(line)
        
        if not relevant_lines:
            return node

        # --- Extract Dates from the entire block ---
        all_dates = []
        for line in relevant_lines:
            all_dates.extend(line.extract_dates())
        if all_dates:
            node.start_date = ParsedField(all_dates[0], 0.9)
            if len(all_dates) > 1:
                node.end_date = ParsedField(all_dates[-1], 0.9)

        # --- Strategy 1: School on line 1, Degree on line 2 ---
        if len(relevant_lines) >= 2 and self._score_school(relevant_lines[0]) > 0.7 and self._score_degree(relevant_lines[1]) > 0.5:
            node.school = ParsedField(self._clean_text(relevant_lines[0].raw), 0.9)
            node.degree = ParsedField(self._clean_text(relevant_lines[1].raw), 0.9)
            return node

        # --- Strategy 2: Split squashed lines and tabular text ---
        full_text = " ".join(l.raw for l in relevant_lines)
        school_keyword_regex = r'\s+(' + '|'.join(self.ctx.school_keywords) + r')'
        parts = re.split(school_keyword_regex, full_text, maxsplit=1, flags=re.I)

        if len(parts) > 2: # split results in 3 parts: [before, keyword, after]
            degree_candidate = self._clean_text(parts[0])
            school_and_desc = parts[1] + parts[2]

            # Heuristic: School name often ends at a period. The rest is description.
            match = re.search(r'\.\s+', school_and_desc)
            if match:
                split_point = match.start()
                school_text = school_and_desc[:split_point + 1]
                desc_text = school_and_desc[split_point + 1:]
            else:
                school_text = school_and_desc
                desc_text = ""

            node.degree = ParsedField(degree_candidate, 0.7)
            node.school = ParsedField(self._clean_text(school_text).strip(), 0.7)
            if desc_text.strip():
                node.description.append(self._clean_text(desc_text).strip())
        else:
            # --- Strategy 3: Fallback to best-scoring line ---
            best_degree_line = max(relevant_lines, key=self._score_degree, default=None)
            best_school_line = max(relevant_lines, key=self._score_school, default=None)

            if best_degree_line and self._score_degree(best_degree_line) > 0.3:
                node.degree = ParsedField(self._clean_text(best_degree_line.raw), 0.5)
            
            if best_school_line and self._score_school(best_school_line) > 0.3:
                # If school and degree were found on the same line, clean the school text
                # Only assign school if it's a different line from the degree,
                # to avoid the school field being polluted on squashed lines.
                if best_school_line != best_degree_line:
                    node.school = ParsedField(self._clean_text(best_school_line.raw), 0.5)

        if node.degree.value is None:
            self.issues.append(ParseIssue(
                section="education",
                message="Could not identify degree in block",
                line_number=block[0].line_number if block else None,
            ))

        return node

    def _clean_text(self, text: str) -> str:
        """Removes dates, GPAs, and other noise from extracted strings."""
        text = re.sub(r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[\s.,]+\d{4}', '', text, flags=re.I)
        text = re.sub(r'\b(?:19|20)\d{2}\b', '', text)
        text = re.sub(r'\b(gpa|cgpa|rank|score|cpi)[\s:.]*[\d./\s]+(out\s+of\s+\d+)?', '', text, flags=re.I)
        text = text.replace("()", "")
        return text.strip(" ,-•·▪▸*()")

    #private helper 
    def _assign_dates(self, line: Line, node: EducationNode | ExperienceNode, score: float):
        """Extracts and assigns dates to a node if the score is high enough."""
        if score < 0.8:
            return
        
        dates = line.extract_dates()
        if dates:
            node.start_date = ParsedField(dates[0], score)
            if len(dates) > 1:
                node.end_date = ParsedField(dates[1], score)

    #scoring ────

    def _score_degree(self, line: Line) -> float:
        text  = line.text_lower()
        score = 0.0
        if any(kw in text for kw in self.ctx.degree_keywords):
            score += 0.8
        if line.word_count() <= 8:
            score += 0.1
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
        return max(0.0, min(score, 1.0))

    def _score_date_range(self, line: Line) -> float:
        date_tokens = [t for t in line.tokens if t.type in DATE_TYPES]
        if not date_tokens:
            return 0.0
        if any(t.type in {"DATE_RANGE", "YEAR_RANGE"} for t in date_tokens):
            return 0.95
        if len(date_tokens) >= 2:
            return 0.95     # "Sep 2018 – May 2022" — very high confidence
        if len(date_tokens) == 1:
            return 0.80     # single date or "Sep 2018 – Present"
        return 0.0

    #internal → Pydantic ─

    @staticmethod
    def _to_model(node: EducationNode) -> Education:
        desc = " ".join(node.description) if node.description else None
        return Education(
            degree=node.degree.value     or "",
            school=node.school.value     or "",
            start_date=node.start_date.value,
            end_date=node.end_date.value,
            description=desc,
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
        
        def _clean_text_from_dates(line: Line) -> str:
            text = line.raw
            for token in line.tokens:
                if token.type in DATE_TYPES:
                    text = text.replace(token.value, "")
            return text.strip(" ,-")

        for line in block:
            # 1 — Date range (most unambiguous)
            if not node.start_date.value:
                self._assign_dates(line, node, self._score_date_range(line))

            role_score = self._score_role(line)
            company_score = self._score_company(line)

            # 2 — Squashed line handling
            if role_score > 0.5 and company_score > 0.4:
                cleaned_text = _clean_text_from_dates(line)
                if role_score>=company_score:
                    if node.role.value is None:
                        node.role = ParsedField(cleaned_text, role_score)
                else:
                    if node.company.value is None:
                        node.company = ParsedField(cleaned_text, company_score)
                continue

            # 3 — Description line
            if self._is_description(line):
                node.description.append(line.raw.strip())
                continue
            # 4 — Role line
            if role_score > 0.5 and node.role.value is None:
                node.role = ParsedField(_clean_text_from_dates(line), role_score)
                continue

            # 5 — Company line
            if company_score > 0.4 and node.company.value is None:
                node.company = ParsedField(_clean_text_from_dates(line), company_score)
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

    #private helper
    def _assign_dates(self, line: Line, node: EducationNode | ExperienceNode, score: float):
        """Extracts and assigns dates to a node if the score is high enough."""
        if score < 0.8:
            return
        
        dates = line.extract_dates()
        if dates:
            node.start_date = ParsedField(dates[0], score)
            if len(dates) > 1:
                node.end_date = ParsedField(dates[1], score)


    #classifiers (section-specific — no global LineType enum) ────

    def _is_description(self, line: Line) -> bool:
        """High token count or starts with a known action verb."""
        if len(line.tokens) > 8:
            return True
        first_word = line.tokens[0].value.lower() if line.tokens else ""
        return first_word in self._ACTION_VERBS

    def _score_date_range(self, line: Line) -> float:
        date_tokens = [t for t in line.tokens if t.type in DATE_TYPES]
        if not date_tokens:
            return 0.0
        if any(t.type in {"DATE_RANGE", "YEAR_RANGE"} for t in date_tokens):
            return 0.95
        if len(date_tokens) >= 2:
            return 0.95
        if len(date_tokens) == 1:
            return 0.80
        return 0.0

    def _score_role(self, line: Line) -> float:
        text  = line.text_lower()
        score = 0.0
        if any(kw in text for kw in self.ctx.role_keywords):
            score += 0.7
        if line.word_count() <= 5:
            score += 0.1
        return max(0.0, min(score, 1.0))

    def _score_company(self, line: Line) -> float:
        text  = line.text_lower()
        score = 0.0
        if any(sfx in text for sfx in self.ctx.company_suffixes):
            score += 0.7
        # Title-case short line — likely a proper noun (company name)
        if line.raw.istitle() and line.word_count() <= 4:
            score += 0.4
        if line.has_date():
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

    Upgraded to more robustly handle various formats by:
    1. Pre-processing lines to strip category labels (e.g., "Languages:").
    2. Consolidating all text into a single block.
    3. Using a powerful regex to split on multiple delimiters (`,`, `|`, `•`, etc.).
    4. Filtering the results against a more comprehensive list of non-skill keywords.
    """

    _STRIP_CHARS = ",.·•*▪▸-–— \t"
    # A more comprehensive set of keywords to filter out.
    _NON_SKILL_KEYWORDS: Set[str] = {
        # Category headers
        "skills", "technical", "computer", "professional", "soft", "hard",
        "languages", "frameworks", "libraries", "tools", "platforms", "databases",
        "concepts", "paradigms", "methodologies", "operating systems", "os",
        "technologies", "competencies", "expertise", "systems",
        # Filler/stop words
        "proficient", "familiar", "experience", "experienced", "knowledge",
        "other", "miscellaneous", "etc", "including", "technologies",
        "and", "in", "with", "of", "for", "the", "a", "an", "at", "to",
        "is", "are", "be", "strong", "good", "excellent", "working", "ability",
    }

    def parse(self, section: Optional[Section]) -> List[str]:
        if section is None:
            return []

        # 1. Pre-process lines to remove category labels and join them.
        processed_lines = []
        for line in section.lines:
            if line.is_blank():
                continue
            
            text = line.raw.strip(self._STRIP_CHARS)
            
            # Heuristic: If a line contains a colon, it might be a "Category: Skills" line.
            if ':' in text:
                parts = text.split(':', 1)
                category_candidate = parts[0].lower().strip()
                # If the part before the colon looks like a category, use only the part after.
                if any(kw in category_candidate for kw in self._NON_SKILL_KEYWORDS) and len(category_candidate.split()) <= 3:
                    text = parts[1]
            
            processed_lines.append(text.strip())

        full_text = ", ".join(filter(None, processed_lines))
        potential_skills = re.split(r'\s*[,|;/]\s*|\s+[•·▪▸]\s+', full_text)

        seen: Set[str] = set()
        result: List[str] = []
        for s in potential_skills:
            s_clean = s.strip(self._STRIP_CHARS)
            key = s_clean.lower()
            if key and key not in seen and key not in self._NON_SKILL_KEYWORDS:
                seen.add(key)
                result.append(s_clean)
        return result

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
        name_candidates: List[Tuple[float, str, int]] = []  # (score, name, line_num)

        for line in lines:
            if line.is_blank():
                continue

            # Email, Phone, URL are strong signals, extract them first.
            if not node.email and line.has_type("EMAIL"):
                node.email = self._first_of_type(line, "EMAIL")
            if not node.phone and line.has_type("PHONE"):
                node.phone = self._first_of_type(line, "PHONE")
            if line.has_type("URL"):
                node.urls.append(self._first_of_type(line, "URL"))

            # Score every line in the header as a potential name
            score = self._score_name_line(line)
            if score > 0.4:  # Confidence threshold to gather candidates
                name_candidates.append((score, line.raw.strip(), line.line_number))

        # If we have candidates, pick the best one.
        if name_candidates:
            # Sort by score (desc) then by line number (asc) as a tie-breaker
            name_candidates.sort(key=lambda x: (-x[0], x[2]))
            best_name = name_candidates[0][1]

            # Final sanity check: don't pick a name that is also the email/phone.
            if best_name != node.email and best_name != node.phone:
                node.name = best_name

        return node

    def _score_name_line(self, line: Line) -> float:
        """Scores a line on how likely it is to be a person's name."""
        # Strong disqualifiers: if it contains these, it's definitely not a name.
        if (line.has_type("EMAIL") or
            line.has_type("PHONE") or
            line.has_type("URL") or
            any(t.type in DATE_TYPES for t in line.tokens) or
            any(char.isdigit() for char in line.raw)):
            return 0.0

        text_lower = line.text_lower()
        address_keywords = {"apt", "rd", "room", "st", "street", "road", "apartment", "pincode", "district", "city", "state"}
        if any(kw in text_lower for kw in address_keywords):
            return 0.0

        meta_keywords = {"resume", "curriculum vitae", "bio-data", "profile"}
        if any(kw in text_lower for kw in meta_keywords):
            return 0.0

        # A section header is not a name.
        if self._is_section_header(line):
            return 0.0

        score = 0.0
        # Positive signals that increase the score
        if line.all_word_types(): score += 0.5
        if 2 <= line.word_count() <= 4: score += 0.3  # Names are usually 2-4 words
        if line.raw.istitle(): score += 0.3           # Names are usually in Title Case
        if line.line_number <= 3: score += 0.2        # Names usually appear at the very top

        # Negative signals (penalties) that decrease the score
        if line.word_count() > 5: score -= 0.4
        if any(p in line.raw for p in [',', ';', ':', '|', '(', ')']): score -= 0.7

        return max(0.0, min(score, 1.0))

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
        "relevant experience":        "experience",
        "employment":                 "experience",
        "research experience":        "experience",
        "academic background":        "education",
        "educational qualification":  "education",
        "educational qualifications": "education",
        "academic qualifications":    "education",
        "academic details":           "education",
        "education & credentials":    "education",
        "academic profile":           "education",
        "technical skills":           "skills",
        "core competencies":          "skills",
        "key skills":                 "skills",
        "areas of expertise":         "skills",
        "professional skills":        "skills",
        "computer skills":            "skills",
        "technical expertise":        "skills",
        "skill set":                  "skills",
        "projects":                   "projects",
        "personal projects":          "projects",
        "academic projects":          "projects",
        "certifications":             "certifications",
        "certificates":               "certifications",
        "licenses & certifications":  "certifications",
        "awards":                     "awards",
        "awards and honors":          "awards",
        "honors and awards":          "awards",
        "honours":                    "awards",
        "honors":                     "awards",
        "publications":               "publications",
        "research papers":            "publications",
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