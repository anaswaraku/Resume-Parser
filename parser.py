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
from utils.key_words import SECTION_KW
from ast_models import Education, Experience, ResumeAST
import re 
from utils.regex_patterns import DATE_RANGE_RE, YEAR_RANGE_RE, DATE_RE, YEAR_RE, RANGE_SEP_STR
 
from dataclasses import dataclass, field
from typing import List
from abc import ABC,abstractmethod 
 
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
  
    def find_header(self, lines):
        normalizer = Normalizer()
        normalized_lines=[]
        for line in lines:
            normalized_lines.append(normalizer._normalize_line(line=line))
        
        sections = []
        current_section = None

        for originial, normalized in zip(lines,normalized_lines):
            header = None 
            # Heuristic: headers are short and not blank.
            if not normalized.is_blank() and normalized.word_count() < 6:
                line_text = normalized.text_lower()
                for key, aliases in SECTION_KW.items():
                    # Use regex to find whole-word matches for any alias.
                    # This is more flexible than exact line matching.
                    if any(re.search(r'\b' + re.escape(a.lower()) + r'\b', line_text) for a in aliases):
                        header = key
                        break
            if header:
                current_section = Section(header=header)
                sections.append(current_section)
            elif current_section:
                current_section.lines.append(originial)
        return sections
                
            
@dataclass
class Section:
    header: str
    lines: list[Line] = field(default_factory=list)

@dataclass
class ParsedSection:
    header: str
    raw: str    

class SectionParser(ABC):
    SECTION_NAME = None
    parsed = None

    @staticmethod
    def _filter_lines(lines: List[Line]) -> List[Line]:
        """Removes blank lines and common separator lines."""
        def is_separator(line_raw: str) -> bool:
            # A line is a separator if it's long and consists of only a few distinct characters
            stripped = line_raw.strip()
            return len(stripped) > 10 and len(set(stripped)) <= 2 and all(c in '_-' for c in set(stripped))

        return [line for line in lines if not line.is_blank() and not is_separator(line.raw)]

    @classmethod
    def parse(cls,sections):
            # Find all sections that match this parser's target header
            target_sections = [s for s in sections if s.header == cls.SECTION_NAME]
            # Let the subclass process the list of full Section objects
            return cls.process(target_sections)

    @classmethod
    def parse_all(cls,sections):
        result={}
        
        for parser in cls.__subclasses__():
            if parser.SECTION_NAME:
                result[parser.SECTION_NAME.lower()]=parser.parse(sections)
        return result
    
    @classmethod
    @abstractmethod
    def process(cls, sections: List[Section]):
        pass

@dataclass
class Summary:
    text: Optional[str]

class SummaryParser(SectionParser):
    SECTION_NAME="SUMMARY"
    
    @classmethod
    def process(cls, sections: List[Section]):
        if not sections:
            return Summary(text=None)
        
        all_lines = [line for s in sections for line in s.lines]
        filtered_lines = SectionParser._filter_lines(all_lines)
        full_summary_text = "\n".join(line.raw for line in filtered_lines)
        return Summary(text=full_summary_text)

class EducationParser(SectionParser):
    SECTION_NAME = 'EDUCATION'

    @classmethod
    def process(cls, sections: List[Section]) -> List[Education]:
        normalizer = Normalizer()
        raw_lines = [line for section in sections for line in section.lines]
        filtered_lines = SectionParser._filter_lines(raw_lines)
        all_lines = normalizer.normalize(filtered_lines)

        # Group lines into entries based on blank lines
        entries_lines: List[List[Line]] = []
        current_entry: List[Line] = []
        for line in all_lines:
            if line.is_blank():
                if current_entry:
                    entries_lines.append(current_entry)
                current_entry = []
            else:
                current_entry.append(line)
        if current_entry:
            entries_lines.append(current_entry)

        # Parse each entry
        education_entries = []
        for entry_lines in entries_lines:
            parsed = cls._parse_entry(entry_lines)
            if parsed.degree or parsed.school:  # Only add if we found something
                education_entries.append(parsed)

        return education_entries

    @classmethod
    def _parse_entry(cls, entry_lines: List[Line]) -> Education:
        # Pre-filter lines to remove noise and stop at irrelevant sections
        filtered_lines = []
        stop_keywords = ['relevant coursework', 'gpa']
        for line in entry_lines:
            raw_lower = line.raw.lower()
            if any(kw in raw_lower for kw in stop_keywords):
                break
            filtered_lines.append(line)

        full_text = " \n ".join(line.raw for line in filtered_lines)

        start_date, end_date = None, None

        # 1. Find and extract dates
        range_match = DATE_RANGE_RE.search(full_text) or YEAR_RANGE_RE.search(full_text)
        if range_match:
            date_str = range_match.group(0)
            full_text = full_text.replace(date_str, "")
            parts = re.split(RANGE_SEP_STR, date_str, flags=re.IGNORECASE)
            if len(parts) >= 2:
                start_date = parts[0].strip()
                end_date = parts[-1].strip()
        else:
            dates = DATE_RE.findall(full_text) + YEAR_RE.findall(full_text)
            if dates:
                years = [int(y) for y in re.findall(r'\d{4}', " ".join(dates))]
                if years:
                    # Use set to handle single graduation year correctly
                    start_date = str(min(years)) if len(set(years)) > 1 else None
                    end_date = str(max(years))
                for d in dates:
                    full_text = full_text.replace(d, "")

        # 2. Parse degree and school from remaining text
        # Remove common noise words before splitting
        full_text = re.sub(r'(?i)\bgraduation:?\b', '', full_text)
        clean_text = re.sub(r'[\s,]+$', '', full_text.strip())
        clean_text = re.sub(r'^\s*[\-,•·▪▸*]\s*', '', clean_text)
        
        text_blob = ", ".join(p.strip() for p in clean_text.split('\n') if p.strip())
        comma_parts = [p.strip() for p in text_blob.split(',') if p.strip()]

        school_part = None
        school_index = -1
        degree = None
        school = None

        for i, part in enumerate(comma_parts):
            if any(kw in part.lower() for kw in ['university', 'college', 'institute', 'school']):
                school_part = part
                school_index = i
                break
        
        if school_part:
            school_parts = [school_part]
            # Also grab subsequent parts that look like a location
            for part in comma_parts[school_index + 1:]:
                # Heuristic: location parts are short and don't contain digits (not a GPA)
                if len(part.split()) < 4 and not any(char.isdigit() for char in part):
                    school_parts.append(part)
                else:
                    break  # Stop if we hit something long or with numbers
            
            school = ", ".join(school_parts)
            degree_parts = comma_parts[:school_index]
            degree = ", ".join(d for d in degree_parts if d).strip()
        elif comma_parts:
            # Fallback: assume degree is first, school is second
            degree = comma_parts[0]
            if len(comma_parts) > 1:
                school = comma_parts[1]

        return Education(degree=degree, school=school, start_date=start_date, end_date=end_date)

class SkillParser(SectionParser):
    SECTION_NAME = 'SKILLS'

    @classmethod
    def process(cls, sections: List[Section]) -> List[str]:
        if not sections:
            return []

        normalizer = Normalizer()
        raw_lines = [line for section in sections for line in section.lines]
        filtered_lines = SectionParser._filter_lines(raw_lines)
        all_lines = normalizer.normalize(filtered_lines)

        # Regex to split by common delimiters like commas, pipes, bullets, and newlines.
        delimiters = re.compile(r'[,|•·▪▸*;/\n]')
        # Regex to remove category prefixes like "Languages:", "Tools:", etc.
        category_prefix = re.compile(r'^[\w\s()\-]+:\s*')

        found_skills = set()

        for line in all_lines:
            # First, remove category prefix from the whole line
            line_content = category_prefix.sub('', line.raw).strip()

            # Now, split the remaining content by delimiters
            parts = delimiters.split(line_content)
            for part in parts:
                cleaned_part = part.strip()
                if cleaned_part:
                    found_skills.add(cleaned_part)

        return sorted(list(found_skills))

class ExperienceParser(SectionParser):
    SECTION_NAME = 'EXPERIENCES'

    @classmethod
    def process(cls, sections: List[Section]) -> List[Experience]:
        normalizer = Normalizer()
        raw_lines = [line for section in sections for line in section.lines]
        filtered_lines = SectionParser._filter_lines(raw_lines)
        all_lines = normalizer.normalize(filtered_lines)

        # Group entries by blank lines.
        entries_lines: List[List[Line]] = []
        current_entry: List[Line] = []
        for line in all_lines:
            if line.is_blank():
                if current_entry:
                    entries_lines.append(current_entry)
                current_entry = []
            else:
                current_entry.append(line)
        if current_entry:
            entries_lines.append(current_entry)

        # If no entries were found via blank lines, treat the whole section as one entry.
        if not entries_lines and all_lines:
            entries_lines.append([line for line in all_lines if not line.is_blank()])

        experience_entries = []
        for entry_lines in entries_lines:
            parsed = cls._parse_entry(entry_lines)
            if parsed.company or parsed.role:
                experience_entries.append(parsed)

        return experience_entries

    @classmethod
    def _parse_entry(cls, entry_lines: List[Line]) -> Experience:
        full_text = "\n".join(line.raw for line in entry_lines)

        start_date, end_date = None, None
        role, company = None, None

        # 1. Find and extract date range
        range_match = DATE_RANGE_RE.search(full_text) or YEAR_RANGE_RE.search(full_text)
        if range_match:
            date_str = range_match.group(0)
            full_text = full_text.replace(date_str, "", 1).strip()
            parts = re.split(RANGE_SEP_STR, date_str, flags=re.IGNORECASE)
            if len(parts) >= 2:
                start_date = parts[0].strip()
                end_date = parts[-1].strip()

        lines = [line.strip() for line in full_text.split('\n') if line.strip()]
        if not lines:
            return Experience(start_date=start_date, end_date=end_date)

        # 2. Find role and company
        separator_re = re.compile(r'\s+[\-–—|@]\s+')
        
        role_company_line_idx = -1
        # Find a line with "Role - Company" pattern
        for i, line in enumerate(lines):
            # Heuristic: role/company line is usually short and not a bullet point
            if separator_re.search(line) and len(line.split()) < 10 and not line.startswith('•'):
                parts = separator_re.split(line, 1)
                role, company = parts[0].strip(), parts[1].strip()
                role_company_line_idx = i
                break
        
        description_lines = []
        if role_company_line_idx != -1:
            # Found role and company on the same line
            description_lines = [line for i, line in enumerate(lines) if i != role_company_line_idx]
        elif lines:
            # Fallback: No separator found. Assume first line is role.
            role = lines[0]
            # The next lines are description
            description_lines = lines[1:]

        description = "\n".join(description_lines).strip()

        return Experience(company=company, role=role, start_date=start_date, end_date=end_date, description=description if description else None)

class ResumeParser:
    def build(self, tokens:List[Token]):
        lines = LineBuilder().build(tokens=tokens)
        
        # 1. Extract name, email, phone from the top of the resume
        name, email, phone = self._parse_contact_info(lines)

        # 2. Parse all other sections using the existing section parsers
        headers = HeaderBuilder().find_header(lines=lines)
        parsed_sections = SectionParser.parse_all(sections=headers)

        # 3. Assemble the final dictionary in the desired format
        education_list = parsed_sections.get('education', [])
        experience_list = parsed_sections.get('experiences', [])
        skills_list = parsed_sections.get('skills', [])

        # The section parsers return Pydantic models or lists of them,
        # which FastAPI will automatically serialize to JSON.
        final_result = {
            "name": name,
            "email": email,
            "phone": phone,
            "education": education_list,
            "experience": experience_list,
            "skills": skills_list,
        }
        return ResumeAST(**final_result)

    def _parse_contact_info(self, lines: List[Line]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        email, phone, name = None, None, None
        
        # Limit search to the top of the resume (first 10 lines)
        contact_lines = lines[:10]

        for line in contact_lines:
            if line.is_blank():
                continue
            
            # Extract email and phone from tokens if not already found
            if not email:
                email_token = next((t.value for t in line.tokens if t.type == "EMAIL"), None)
                if email_token:
                    email = email_token
            
            if not phone:
                phone_token = next((t.value for t in line.tokens if t.type == "PHONE"), None)
                if phone_token:
                    phone = phone_token

        # Heuristic for name: Find the first plausible line at the top.
        # Usually the first non-blank line, short, and not contact info or a header.
        for line in lines[:5]:
            if not line.is_blank() and not line.has_type("EMAIL") and not line.has_type("PHONE") and not line.has_type("URL"):
                # A name is typically 2-4 words.
                if 1 <= line.word_count() <= 4:
                    name = line.raw
                    break # Found a plausible name, so we stop.

        return name, email, phone