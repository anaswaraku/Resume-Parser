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
from utils.regex_patterns import DATE_RANGE_RE, YEAR_RANGE_RE, DATE_RE, YEAR_RE, RANGE_SEP_STR, YEAR_STR, PRESENT_STR
 
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
            if not normalized.is_blank() and normalized.word_count() < 8:
                # Strip trailing colons and punctuation for matching
                line_text = re.sub(r'[:\s]+$', '', normalized.text_lower())
                best_match_key = None
                best_match_len = -1
                for key, aliases in SECTION_KW.items():
                    for a in aliases:
                        if re.search(r'\b' + re.escape(a.lower()) + r'\b', line_text):
                            if len(a) > best_match_len:
                                best_match_len = len(a)
                                best_match_key = key
                if best_match_key:
                    header = best_match_key
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

    # Regex that recognises a leading year-range like "2010–Now" or "2007–2010"
    _LEADING_DATE_RE = re.compile(
        r'^\s*(?:'
        + YEAR_STR + r'(?:\s*[-–—]+\s*|\s+to\s+)(?:' + YEAR_STR + r'|\d{2}|' + PRESENT_STR + r')'
        + r'|' + YEAR_STR
        + r')\b',
        re.IGNORECASE,
    )

    # Keywords indicating degree-level information
    _DEGREE_KW = re.compile(
        r'(?i)\b(?:bachelor|master|'
        r'p\.?h\.?\s*d\.?|phd|diploma|'
        r'b\.?\s*tech|b\.?\s*e\b|b\.?\s*sc|b\.?\s*com|'
        r'b\.?\s*a\b|m\.?\s*tech|m\.?\s*e\b|m\.?\s*sc|m\.?\s*b\.?\s*a|'
        r'b\.?s\.?|m\.?s\.?|associate|class\s+[xiv]+|\bxii\b|\bx\b|'
        r'pursuing)'
    )

    # Words that appear together in table-header rows — not real education data
    _TABLE_HEADER_WORDS = {
        'year', 'degree', 'institute', 'college', 'university',
        'percentage', 'cgpa', 'marks', 'grade', 'board', 'stream',
    }

    # Placeholder dates like "May 20XX" or just "20XX" / "19XX"
    _PLACEHOLDER_DATE_RE = re.compile(
        r'(?i)\b(?:january|february|march|april|may|june|july|august|september|october|november|december'
        r'|jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)'
        r'\.?\s*(?:19|20)[xX]{2}\b'
        r'|\b(?:19|20)[xX]{2}\b'
    )

    @classmethod
    def _is_table_header(cls, line: Line) -> bool:
        """True if a line looks like a table column-header row (not real edu data)."""
        words = set(re.findall(r'[a-z]+', line.raw.lower()))
        matches = words & cls._TABLE_HEADER_WORDS
        # Flag if >=3 header words present, or 2+ and the line has no digit run (no year)
        return len(matches) >= 3 or (len(matches) >= 2 and not re.search(r'\d{4}', line.raw))

    @classmethod
    def process(cls, sections: List[Section]) -> List[Education]:
        normalizer = Normalizer()
        raw_lines = [line for section in sections for line in section.lines]
        # Remove table-header rows before anything else
        raw_lines = [l for l in raw_lines if not cls._is_table_header(l)]
        filtered_lines = SectionParser._filter_lines(raw_lines)
        all_lines = normalizer.normalize(filtered_lines)

        # --- Split lines into entry groups ---
        entries_lines = cls._split_by_blanks(all_lines)
        if len(entries_lines) <= 1 and all_lines:
            date_split = cls._split_by_leading_dates(all_lines)
            if len(date_split) > len(entries_lines):
                entries_lines = date_split

        # If still one big group, try degree-keyword splitting
        if len(entries_lines) <= 1 and all_lines:
            degree_split = cls._split_by_degree_keywords(all_lines)
            if len(degree_split) > len(entries_lines):
                entries_lines = degree_split

        # Parse each entry
        education_entries = []
        for entry_lines in entries_lines:
            parsed = cls._parse_entry(entry_lines)
            if parsed.degree or parsed.school:  # Only add if we found something
                education_entries.append(parsed)

        return education_entries

    @classmethod
    def _split_by_blanks(cls, lines: List[Line]) -> List[List[Line]]:
        """Group lines into entries based on blank lines."""
        entries: List[List[Line]] = []
        current: List[Line] = []
        for line in lines:
            if line.is_blank():
                if current:
                    entries.append(current)
                current = []
            else:
                current.append(line)
        if current:
            entries.append(current)
        return entries

    @classmethod
    def _split_by_leading_dates(cls, lines: List[Line]) -> List[List[Line]]:
        """Split entries when a line starts with a year or year-range (e.g. '2010–Now')."""
        entries: List[List[Line]] = []
        current: List[Line] = []
        for line in lines:
            if line.is_blank():
                continue
            if cls._LEADING_DATE_RE.match(line.raw.strip()) and current:
                entries.append(current)
                current = []
            current.append(line)
        if current:
            entries.append(current)
        return entries

    @classmethod
    def _split_by_degree_keywords(cls, lines: List[Line]) -> List[List[Line]]:
        """Split entries when a line contains a degree keyword (Bachelor, Master, etc.)."""
        entries: List[List[Line]] = []
        current: List[Line] = []
        for line in lines:
            if line.is_blank():
                continue
            if cls._DEGREE_KW.search(line.raw) and current:
                entries.append(current)
                current = []
            current.append(line)
        if current:
            entries.append(current)
        return entries

    @classmethod
    def _parse_entry(cls, entry_lines: List[Line]) -> Education:
        # Pre-filter lines to remove noise and stop at irrelevant metadata
        filtered_lines = []
        stop_keywords = ['relevant coursework', 'gpa', 'advisor:', 'thesis:', 'ranked']
        for line in entry_lines:
            raw_lower = line.raw.lower()
            if any(kw in raw_lower for kw in stop_keywords):
                break
            filtered_lines.append(line)

        if not filtered_lines:
            filtered_lines = entry_lines[:2]  # fallback: use first two lines

        # Fix 5: join hyphen-terminated lines directly (PDF line-wrap artifact)
        joined_lines: List[str] = []
        carry = ""
        for line in filtered_lines:
            raw = line.raw.rstrip()
            if carry:
                raw = carry + raw
                carry = ""
            if raw.endswith("-") and not re.search(
                r'(?i)\b(?:' + '|'.join([
                    'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
                ]) + r')\b.*-$', raw
            ):
                # trailing hyphen = word-wrap; carry forward without the hyphen
                carry = raw[:-1]
            else:
                joined_lines.append(raw)
        if carry:
            joined_lines.append(carry)

        full_text = " \n ".join(joined_lines)

        start_date, end_date = None, None

        # 1. Find and extract dates
        range_match = DATE_RANGE_RE.search(full_text) or YEAR_RANGE_RE.search(full_text)
        if range_match:
            date_str = range_match.group(0)
            full_text = full_text.replace(date_str, "")
            parts = re.split(RANGE_SEP_STR, date_str, flags=re.IGNORECASE)
            # Filter out empty parts from the split
            parts = [p.strip() for p in parts if p.strip()]
            if len(parts) >= 2:
                start_date = parts[0].strip()
                end_date = parts[-1].strip()
            elif len(parts) == 1:
                end_date = parts[0].strip()
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
        # Remove page markers like "Page 2of 3" / "1of 3"
        full_text = re.sub(r'(?i)\b(?:page\s*)?\d+\s*of\s*\d+\b', '', full_text)
        # Fix 6: Strip placeholder dates like "May 20XX" or "20XX"
        full_text = cls._PLACEHOLDER_DATE_RE.sub('', full_text)
        clean_text = re.sub(r'[\s,]+$', '', full_text.strip())
        clean_text = re.sub(r'^\s*[\-,•·▪▸*]\s*', '', clean_text)

        text_blob = ", ".join(p.strip() for p in clean_text.split('\n') if p.strip())
        comma_parts = [p.strip() for p in text_blob.split(',') if p.strip()]

        school_part = None
        school_index = -1
        degree = None
        school = None

        # Extended school keywords
        school_keywords = ['university', 'college', 'institute', 'school', 'academy', 'polytechnic']

        # Fix 4: If a single comma-part contains BOTH a degree keyword AND a school keyword,
        # split that part inline at the school keyword boundary.
        expanded_parts: List[str] = []
        for part in comma_parts:
            part_lower = part.lower()
            has_degree = bool(cls._DEGREE_KW.search(part))
            school_kw_match = next((kw for kw in school_keywords if kw in part_lower), None)
            if has_degree and school_kw_match:
                # Split at the first occurrence of the school keyword
                idx = part_lower.index(school_kw_match)
                before = part[:idx].strip().rstrip(',').strip()
                after = part[idx:].strip()
                if before:
                    expanded_parts.append(before)
                if after:
                    expanded_parts.append(after)
            else:
                expanded_parts.append(part)
        comma_parts = [p for p in expanded_parts if p]

        for i, part in enumerate(comma_parts):
            if any(kw in part.lower() for kw in school_keywords):
                school_part = part
                school_index = i
                break

        if school_part:
            school_parts = [school_part]
            # Also grab subsequent parts that look like a location
            for part in comma_parts[school_index + 1:]:
                # Heuristic: location parts are short and don't contain digits (not a GPA)
                if len(part.split()) < 5 and not any(char.isdigit() for char in part):
                    school_parts.append(part)
                else:
                    break  # Stop if we hit something long or with numbers

            school = ", ".join(school_parts)
            degree_parts = comma_parts[:school_index]
            degree = ", ".join(d for d in degree_parts if d).strip()
        elif comma_parts:
            # Fallback: use degree keyword detection to separate degree from school/field
            degree_idx = -1
            for i, part in enumerate(comma_parts):
                if cls._DEGREE_KW.search(part):
                    degree_idx = i
                    break

            if degree_idx >= 0:
                degree = comma_parts[degree_idx]
                # Remaining parts after degree are school/field
                remaining = [p for j, p in enumerate(comma_parts) if j != degree_idx]
                if remaining:
                    school = ", ".join(remaining)
            else:
                # Last resort: first part is degree, second is school
                degree = comma_parts[0]
                if len(comma_parts) > 1:
                    school = ", ".join(comma_parts[1:])

        # Clean up empty strings
        if degree and not degree.strip():
            degree = None
        if school and not school.strip():
            school = None
        if end_date is not None and not end_date.strip():
            end_date = None

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
    # Common document title patterns to skip when looking for names
    _TITLE_RE = re.compile(
        r'(?i)\b(?:resume|curriculum\s+vitae|c\.?v\.?|bio[- ]?data)\b'
    )
    # Address-like lines: contain digits + typical location words
    _ADDRESS_RE = re.compile(
        r'(?i)\b(?:street|st\.|blvd|avenue|ave\.|road|rd\.|apt|suite|p\.?o\.?\s*box|\d{5})\b'
    )

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

    def _is_section_header(self, line_text: str) -> bool:
        """Check if a line matches any known section header keyword."""
        stripped = re.sub(r'[:\s]+$', '', line_text.lower())
        for _key, aliases in SECTION_KW.items():
            if any(re.search(r'\b' + re.escape(a.lower()) + r'\b', stripped) for a in aliases):
                return True
        return False

    def _is_name_candidate(self, line: Line) -> bool:
        """Return True if the line looks like a person's name."""
        if line.is_blank():
            return False
        # Skip lines with contact tokens
        if line.has_type("EMAIL") or line.has_type("PHONE") or line.has_type("URL"):
            return False
        # Skip lines that are document titles
        if self._TITLE_RE.search(line.raw):
            return False
        # Skip section headers
        if self._is_section_header(line.raw):
            return False
        # Skip address-like lines
        if self._ADDRESS_RE.search(line.raw):
            return False
        # Skip lines with dates
        if line.has_type("DATE") or line.has_type("DATE_RANGE") or line.has_type("YEAR_RANGE"):
            return False
        # A name is typically 1-5 words (allowing for suffixes like ".K.B")
        if not (1 <= line.word_count() <= 5):
            return False
        # Name lines should be mostly alpha characters (allow dots, hyphens, spaces)
        alpha_ratio = sum(1 for c in line.raw if c.isalpha()) / max(len(line.raw), 1)
        if alpha_ratio < 0.5:
            return False
        return True

    def _parse_contact_info(self, lines: List[Line]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        email, phone, name = None, None, None
        
        # Search the top of the resume (first 15 lines) for email and phone
        contact_lines = lines[:15]

        for line in contact_lines:
            if line.is_blank():
                continue
            
            # Extract email and phone from tokens if not already found
            if not email:
                email_token = next((t.value for t in line.tokens if t.type == "EMAIL"), None)
                if email_token:
                    email = email_token
            
            if not phone:
                phone_token = self._pick_best_phone(line)
                if phone_token:
                    phone = phone_token

        # Fix 1: Fallback — scan only lines 15-25 (not the whole doc) to avoid footer emails
        if not email or not phone:
            for line in lines[15:25]:
                if line.is_blank():
                    continue
                if not email:
                    email_token = next((t.value for t in line.tokens if t.type == "EMAIL"), None)
                    if email_token:
                        email = email_token
                if not phone:
                    phone_token = self._pick_best_phone(line)
                    if phone_token:
                        phone = phone_token
                if email and phone:
                    break

        # Heuristic for name: Find the first plausible line at the top.
        # Check first 8 lines, skipping titles, headers, contact-only lines, addresses.
        for line in lines[:8]:
            if self._is_name_candidate(line):
                # Clean up the raw text: remove trailing commas and extra whitespace
                name = re.sub(r'[,;]+$', '', line.raw).strip()
                break

        return name, email, phone

    @staticmethod
    def _pick_best_phone(line: Line) -> Optional[str]:
        """Fix 2: Among all PHONE tokens on a line, prefer one with a country-code prefix."""
        phone_tokens = [t.value for t in line.tokens if t.type == "PHONE"]
        if not phone_tokens:
            return None
        # Prefer tokens that start with '+' or look like international numbers (91..., 1...)
        for tok in phone_tokens:
            if tok.startswith('+') or re.match(r'^(?:91|1)[\s\-]', tok):
                return tok
        return phone_tokens[0]  # fallback: first token found