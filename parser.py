"""
Traditional Parser — extracts name, email, phone, education only.
Experience and skills are left empty for the LLM to fill.
"""
from __future__ import annotations
import re
from typing import List, Optional, Tuple

from lexer import Token
from ast_models import Education, ResumeAST
from utils.key_words import SECTION_KW
from utils.regex_patterns import (
    DATE_RANGE_RE, YEAR_RANGE_RE,
    DATE_RE, YEAR_RE,
    RANGE_SEP_STR, YEAR_STR, PRESENT_STR
)
from dataclasses import dataclass, field
from abc import ABC, abstractmethod


# ─────────────────────────────────────────────
# Line
# ─────────────────────────────────────────────
@dataclass
class Line:
    tokens: List[Token]
    raw: str
    line_number: int

    def is_blank(self) -> bool:
        return len(self.tokens) == 0

    def has_type(self, ttype: str) -> bool:
        return any(t.type == ttype for t in self.tokens)

    def token_types(self) -> List[str]:
        return [t.type for t in self.tokens]

    def word_count(self) -> int:
        return sum(1 for t in self.tokens if t.type == "WORD")

    def text_lower(self) -> str:
        return self.raw.strip().lower()


# ─────────────────────────────────────────────
# LineBuilder
# ─────────────────────────────────────────────
class LineBuilder:
    def build(self, tokens: List[Token]) -> List[Line]:
        lines, current, line_number = [], [], 1
        for token in tokens:
            if token.type == "NEWLINE":
                lines.append(self._make_line(current, line_number))
                current = []
                line_number += 1
            else:
                current.append(token)
        if current:
            lines.append(self._make_line(current, line_number))
        return lines

    @staticmethod
    def _make_line(tokens: List[Token], line_number: int) -> Line:
        return Line(
            tokens=tokens,
            raw=" ".join(t.value for t in tokens),
            line_number=line_number
        )


# ─────────────────────────────────────────────
# Normalizer
# ─────────────────────────────────────────────
class Normalizer:
    RULES = [
        (re.compile(r'\bb\.?\s*tech\.?\b',       re.I), "Bachelor of Technology"),
        (re.compile(r'\bb\.?\s*e\.?\b',          re.I), "Bachelor of Engineering"),
        (re.compile(r'\bb\.?\s*sc\.?\b',         re.I), "Bachelor of Science"),
        (re.compile(r'\bb\.?\s*com\.?\b',        re.I), "Bachelor of Commerce"),
        (re.compile(r'\bb\.?\s*a\.?\b',          re.I), "Bachelor of Arts"),
        (re.compile(r'\bm\.?\s*tech\.?\b',       re.I), "Master of Technology"),
        (re.compile(r'\bm\.?\s*e\.?\b',          re.I), "Master of Engineering"),
        (re.compile(r'\bm\.?\s*sc\.?\b',         re.I), "Master of Science"),
        (re.compile(r'\bm\.?\s*b\.?\s*a\.?\b',  re.I), "Master of Business Administration"),
        (re.compile(r'\bph\.?\s*d\.?\b',         re.I), "PhD"),
        (re.compile(r'\bsept\b',                 re.I), "Sep"),
        (re.compile(r'\b(present|current|now|ongoing|till\s+date|to\s+date)\b', re.I), "Present"),
        (re.compile(r'^[\s•·▪▸\-–—*]+'),         ""),
    ]

    def normalize(self, lines: List[Line]) -> List[Line]:
        return [self._normalize_line(l) for l in lines]

    def _normalize_line(self, line: Line) -> Line:
        if line.is_blank():
            return line
        raw, changed = line.raw, False
        for pattern, replacement in self.RULES:
            new_raw, n = pattern.subn(replacement, raw)
            if n:
                raw = new_raw.strip()
                changed = True
        if not changed:
            return line
        return Line(tokens=line.tokens, raw=raw, line_number=line.line_number)


# ─────────────────────────────────────────────
# Section  (only EDUCATION and contact header)
# ─────────────────────────────────────────────
@dataclass
class Section:
    header: str
    lines: List[Line] = field(default_factory=list)


# Safe aliases — long enough not to fire on body text
_EDUCATION_ALIASES = [
    a.lower() for a in SECTION_KW['EDUCATION']
    if len(a.split()) >= 2 or a in ('EDUCATION',)   # keep 'EDUCATION' but drop 'COURSE'
]

# Pre-sort longest first so "EDUCATIONAL QUALIFICATIONS" beats "EDUCATION"
_EDUCATION_ALIASES.sort(key=len, reverse=True)


class HeaderBuilder:
    """Detects only EDUCATION section headers — ignores everything else."""

    _SECTION_KW_FLAT = [
        (len(alias), ('COURSEWORK' if 'course' in alias.lower() else canonical), alias.lower())
        for canonical, aliases in SECTION_KW.items()
        for alias in aliases
        if len(alias.split()) >= 2 or alias in (
            'EDUCATION', 'SUMMARY', 'SKILLS',
            'EXPERIENCES', 'EXPERIENCE', 'WORK',
            'PROJECTS', 'PROJECT', 'ACHIEVEMENTS', 'CERTIFICATIONS',
            'COURSES', 'LEADERSHIP', 'ACTIVITIES', 'INTERESTS',
            'MEMBERSHIPS', 'PUBLICATIONS', 'PATENTS', 'LANGUAGES',
        )
    ]
    _SECTION_KW_FLAT.sort(key=lambda x: x[0], reverse=True)

    def find_header(self, lines: List[Line]) -> List[Section]:
        normalizer = Normalizer()
        sections: List[Section] = []
        current: Optional[Section] = None

        for original in lines:
            normalized = normalizer._normalize_line(original)
            header_key = None

            if not normalized.is_blank() and normalized.word_count() < 8:
                line_text = re.sub(r'[:\s]+$', '', normalized.text_lower())
                # longest-match wins — stops first hit
                for _, canonical, alias in self._SECTION_KW_FLAT:
                    if re.search(r'\b' + re.escape(alias) + r'\b', line_text):
                        header_key = canonical
                        break

            if header_key:
                current = Section(header=header_key)
                sections.append(current)
            elif current:
                current.lines.append(original)

        return sections


# ─────────────────────────────────────────────
# EducationParser  (self-contained)
# ─────────────────────────────────────────────
class EducationParser:
    _LEADING_DATE_RE = re.compile(
        r'^\s*(?:'
        + YEAR_STR + r'(?:\s*[-–—]+\s*|\s+to\s+)(?:' + YEAR_STR + r'|\d{2}|' + PRESENT_STR + r')'
        + r'|' + YEAR_STR
        + r')\b',
        re.IGNORECASE,
    )

    _DEGREE_KW = re.compile(
        r'(?i)\b(?:bachelor|master|'
        r'p\.?h\.?\s*d\.?|phd|diploma|'
        r'b\.?\s*tech|b\.?\s*e\b|b\.?\s*sc|b\.?\s*com|'
        r'b\.?\s*a\b|m\.?\s*tech|m\.?\s*e\b|m\.?\s*sc|m\.?\s*b\.?\s*a|'
        r'b\.?s\.?|m\.?s\.?|associate|pursuing|'
        r'class\s+(?:x|xii|10|12|10th|12th)|hsc|sslc|ssc|matriculation|high\s*school|cbse|icse)\b'
    )

    _TABLE_HEADER_WORDS = {
        'year', 'degree', 'institute', 'college',
        'university', 'percentage', 'cgpa', 'marks',
        'grade', 'board', 'stream',
    }

    _STOP_RE = re.compile(
        r'\b(?:relevant\s+coursework|advisor|thesis|ranked\s+\d|gpa)\b', re.I
    )

    _PLACEHOLDER_DATE_RE = re.compile(
        r'(?i)\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)'
        r'\.?\s*(?:19|20)[xX]{2}\b|\b(?:19|20)[xX]{2}\b'
    )

    _SCHOOL_KW = ['university', 'college', 'institute', 'school',
                  'academy', 'polytechnic', 'uc', 'iit', 'nit', 'mit', 'bits',
                  'iiit', 'vidhyalaya', 'vidyalaya', 'csu']

    @classmethod
    def _is_table_header(cls, line: Line) -> bool:
        words = set(re.findall(r'[a-z]+', line.raw.lower()))
        if words and words.issubset({
            'year', 'degree', 'institute', 'college', 'university', 'percentage',
            'cgpa', 'marks', 'grade', 'board', 'stream', 'examination', 'obtained',
            'passed', 'class', 'division', 'subject'
        }):
            return True
        matches = words & cls._TABLE_HEADER_WORDS
        return len(matches) >= 3 or (
            len(matches) >= 2 and not re.search(r'\d{4}', line.raw)
        )

    @staticmethod
    def _filter_lines(lines: List[Line]) -> List[Line]:
        def is_sep(raw):
            s = raw.strip()
            return len(s) > 10 and len(set(s)) <= 2 and all(c in '_-' for c in set(s))
        return [l for l in lines if not l.is_blank() and not is_sep(l.raw)]

    # ── entry splitting ──────────────────────────────────────

    @classmethod
    def _split_by_blanks(cls, lines: List[Line]) -> List[List[Line]]:
        """Split on blank lines; blanks must still be present in input."""
        entries, current = [], []
        for line in lines:
            if line.is_blank():
                if current:
                    entries.append(current)
                    current = []
            else:
                current.append(line)
        if current:
            entries.append(current)
        return entries or [[l for l in lines if not l.is_blank()]]

    @classmethod
    def _split_by_leading_dates(cls, lines: List[Line]) -> List[List[Line]]:
        entries, current = [], []
        for line in lines:
            if line.is_blank():
                if current:
                    entries.append(current)
                    current = []
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
        entries, current = [], []
        for line in lines:
            if line.is_blank():
                if current:
                    entries.append(current)
                    current = []
                continue
            if cls._DEGREE_KW.search(line.raw) and current:
                entries.append(current)
                current = []
            current.append(line)
        if current:
            entries.append(current)
        return entries

    @classmethod
    def _split_smart(cls, lines: List[Line]) -> List[List[Line]]:
        entries: List[List[Line]] = []
        current: List[Line] = []
        
        has_school = False
        has_degree = False
        has_date = False
        
        for line in lines:
            if line.is_blank():
                if current:
                    entries.append(current)
                    current = []
                    has_school = has_degree = has_date = False
                continue
                
            line_has_school = any(re.search(r'\b' + re.escape(k) + r'\b', line.raw.lower()) for k in cls._SCHOOL_KW)
            line_has_degree = bool(cls._DEGREE_KW.search(line.raw))
            line_has_date = bool(DATE_RANGE_RE.search(line.raw) or YEAR_RANGE_RE.search(line.raw))
            
            if cls._STOP_RE.search(line.raw):
                line_has_school = False
                line_has_degree = False
            
            should_split = False
            if current:
                if line_has_school and has_school:
                    should_split = True
                elif line_has_degree and has_degree:
                    should_split = True
                elif line_has_date and has_date:
                    should_split = True
                    
            if should_split:
                entries.append(current)
                current = [line]
                has_school = line_has_school
                has_degree = line_has_degree
                has_date = line_has_date
            else:
                current.append(line)
                has_school = has_school or line_has_school
                has_degree = has_degree or line_has_degree
                has_date = has_date or line_has_date
                
        if current:
            entries.append(current)
        return entries

    # ── main process ────────────────────────────────────────

    @classmethod
    def process(cls, sections: List[Section]) -> List[Education]:
        normalizer = Normalizer()
        target = [s for s in sections if s.header == 'EDUCATION']
        if not target:
            return []

        # Collect raw lines — KEEP blanks, they are split signals
        raw_lines = [
            line
            for s in target
            for line in s.lines
            if not cls._is_table_header(line)
        ]

        # 1. Try blank-line split first (most reliable)
        entry_groups = cls._split_by_blanks(raw_lines)

        # 2. Fallback: smart heuristic split (dense single-block resumes or no blanks)
        if len(entry_groups) <= 1:
            non_blank = [l for l in raw_lines if not l.is_blank()]
            smart_groups = cls._split_smart(non_blank)
            if len(smart_groups) > 1:
                entry_groups = smart_groups

        # 4. Filter + normalise WITHIN each group, then parse
        results = []
        for group in entry_groups:
            clean = cls._filter_lines(group)
            clean = normalizer.normalize(clean)
            if not clean:
                continue
            edu = cls._parse_entry(clean)
            if edu.degree or edu.school:
                results.append(edu)

        return results

    # ── entry parsing ────────────────────────────────────────

    @classmethod
    def _parse_entry(cls, entry_lines: List[Line]) -> Education:
        # Remove noise lines
        filtered = []
        for line in entry_lines:
            if cls._STOP_RE.search(line.raw):
                break
            filtered.append(line)
        if not filtered and entry_lines:
            filtered = entry_lines[:1]

        # Join hyphen-wrapped lines (PDF artefact)
        joined: List[str] = []
        carry = ""
        for line in filtered:
            raw = carry + line.raw.rstrip()
            carry = ""
            if raw.endswith("-") and not re.search(
                r'(?i)\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b.*-$', raw
            ):
                carry = raw[:-1]
            else:
                joined.append(raw)
        if carry:
            joined.append(carry)

        full_text = " \n ".join(joined)
        start_date = end_date = None

        # ── Extract dates ────────────────────────────────────
        range_match = DATE_RANGE_RE.search(full_text) or YEAR_RANGE_RE.search(full_text)
        if range_match:
            date_str = range_match.group(0)
            full_text = full_text.replace(date_str, "", 1)
            parts = [p.strip() for p in re.split(RANGE_SEP_STR, date_str, flags=re.IGNORECASE) if p.strip()]
            if len(parts) >= 2:
                start_date, end_date = parts[0], parts[-1]
            elif parts:
                end_date = parts[0]
        else:
            dates = DATE_RE.findall(full_text) + YEAR_RE.findall(full_text)
            if dates:
                year_matches = []
                for d in dates:
                    ym = re.search(r'\b(?:19|20)(?:\d{2}|[xX]{2})\b', d)
                    if ym:
                        year_matches.append((ym.group(0), d))
                
                if year_matches:
                    def sort_key(item):
                        y_str = item[0]
                        if 'X' in y_str.upper():
                            return 9999
                        return int(y_str)
                    
                    sorted_dates = [d for y_str, d in sorted(year_matches, key=sort_key)]
                    if len(sorted_dates) > 1:
                        start_date = sorted_dates[0]
                        end_date = sorted_dates[-1]
                    else:
                        end_date = sorted_dates[0]
                
                for d in dates:
                    full_text = full_text.replace(d, "", 1)

        # ── Clean remaining text ─────────────────────────────
        # Strip GPA/CPI/marks/completed noise from end of lines
        full_text = re.compile(r'\b(?:completed|cpi|cgpa|gpa|percentage|marks|grade|class|division)\b.*$', re.I | re.M).sub('', full_text)
        full_text = re.sub(r'(?i)\bgraduation:?\b', '', full_text)
        full_text = re.sub(r'(?i)\b(?:page\s*)?\d+\s*of\s*\d+\b', '', full_text)
        full_text = cls._PLACEHOLDER_DATE_RE.sub('', full_text)
        full_text = re.sub(r'[\s,]+$', '', full_text.strip())
        full_text = re.sub(r'^\s*[\-,•·▪▸*]\s*', '', full_text)

        text_blob = ", ".join(p.strip() for p in full_text.split('\n') if p.strip())
        parts = [p.strip() for p in text_blob.split(',') if p.strip()]

        # Inline expansion: "BSc Computer Science, MIT" → ["BSc Computer Science", "MIT"]
        expanded = []
        for part in parts:
            has_deg = bool(cls._DEGREE_KW.search(part))
            skw = next((k for k in cls._SCHOOL_KW if k in part.lower()), None)
            if has_deg and skw:
                idx = part.lower().index(skw)
                before, after = part[:idx].strip().rstrip(','), part[idx:].strip()
                if before: expanded.append(before)
                if after:  expanded.append(after)
            else:
                expanded.append(part)
        parts = [p for p in expanded if p]

        # ── Find school and degree ───────────────────────────
        school = degree = None
        school_idx = -1
        for i, part in enumerate(parts):
            if any(re.search(r'\b' + re.escape(k) + r'\b', part.lower()) for k in cls._SCHOOL_KW):
                school_idx = i
                break

        degree_idx = -1
        for i, part in enumerate(parts):
            if cls._DEGREE_KW.search(part):
                degree_idx = i
                break

        if school_idx >= 0:
            # Grab school + subsequent location parts
            school_parts = [parts[school_idx]]
            for part in parts[school_idx + 1:]:
                if cls._DEGREE_KW.search(part):
                    break
                if len(part.split()) < 5 and not any(c.isdigit() for c in part):
                    school_parts.append(part)
                else:
                    break
            school = ", ".join(school_parts)
            
            # Degree is the remaining parts not in school_parts
            deg_parts = []
            for i, part in enumerate(parts):
                if i == school_idx:
                    continue
                if i > school_idx and part in school_parts:
                    continue
                deg_parts.append(part)
            degree = ", ".join(deg_parts).strip() or None
        else:
            # No school keyword found, fallback to heuristics
            if degree_idx >= 0:
                degree = parts[degree_idx]
                other_parts = [p for i, p in enumerate(parts) if i != degree_idx]
                school = ", ".join(other_parts).strip() or None
            else:
                last = parts[-1].strip() if parts else ""
                if re.match(r'^[A-Z]{2,6}$', last):          # "MIT", "IIT", "NTU"
                    school = last
                    degree = ", ".join(parts[:-1]).strip() or None
                elif (last and last[0].isupper()
                      and not cls._DEGREE_KW.search(last)
                      and len(last.split()) <= 4):            # "Carnegie Mellon"
                    school = last
                    degree = ", ".join(parts[:-1]).strip() or None
                elif parts:
                    degree = parts[0]
                    school = ", ".join(parts[1:]) if len(parts) > 1 else None

        # Sanity check: if degree or school is too long (often happens with 2-column resumes mixing experience text), discard it
        if degree:
            degree = re.sub(r'(?i)^\s*(?:pursuing|completed)\s+', '', degree).strip()
            if len(degree.split()) > 10:
                degree = None
        if school and len(school.split()) > 8:
            school = None

        return Education(
            degree=degree or None,
            school=school or None,
            start_date=start_date,
            end_date=end_date,
        )


# ─────────────────────────────────────────────
# ResumeParser  (the public entry point)
# ─────────────────────────────────────────────
class ResumeParser:
    _TITLE_RE   = re.compile(r'(?i)\b(?:resume|curriculum\s+vitae|c\.?v\.?|bio[- ]?data)\b')
    _ADDRESS_RE = re.compile(r'(?i)\b(?:street|st\.|blvd|avenue|ave\.|road|rd\.|apt|suite|p\.?o\.?\s*box|\d{5})\b')

    # All known section aliases (any canonical) — used to stop contact scan
    _ALL_ALIASES_RE = re.compile(
        r'\b(' +
        '|'.join(
            re.escape(alias.lower())
            for aliases in SECTION_KW.values()
            for alias in aliases
            if len(alias.split()) >= 2 or alias in (
                'EDUCATION', 'SUMMARY', 'SKILLS',
                'EXPERIENCE', 'EXPERIENCES', 'PROJECTS',
            )
        ) + r')\b',
        re.IGNORECASE,
    )

    def build(self, tokens: List[Token], raw_text: str = "") -> ResumeAST:
        lines = LineBuilder().build(tokens)

        # ── Personal info (traditional, top-of-doc scan) ──
        name, email, phone = self._parse_contact_info(lines, raw_text)

        # ── Education (traditional) ────────────────────────
        sections  = HeaderBuilder().find_header(lines)
        education = EducationParser().process(sections)

        return ResumeAST(
            name=name,
            email=email,
            phone=phone,
            education=education,
            experience=[],   # LLM fills this
            skills=[],       # LLM fills this
        )

    # ── helpers ──────────────────────────────────────────────

    def _first_section_line(self, lines: List[Line]) -> int:
        """Return the index of the first detected section header."""
        normalizer = Normalizer()
        for i, line in enumerate(lines):
            norm = normalizer._normalize_line(line)
            if norm.is_blank() or norm.word_count() >= 8:
                continue
            text = re.sub(r'[:\s]+$', '', norm.text_lower())
            if self._ALL_ALIASES_RE.search(text):
                return i
        return min(25, len(lines))  # fallback: assume contact in first 25 lines

    def _is_name_candidate(self, line: Line) -> bool:
        if line.is_blank():                                      return False
        if line.has_type("EMAIL") or line.has_type("PHONE"):    return False
        if self._TITLE_RE.search(line.raw):                     return False
        if self._ADDRESS_RE.search(line.raw):                   return False
        if line.has_type("DATE") or line.has_type("YEAR_RANGE"): return False
        if not (1 <= line.word_count() <= 5):                   return False
        alpha_ratio = sum(1 for c in line.raw if c.isalpha()) / max(len(line.raw), 1)
        return alpha_ratio >= 0.5

    def _parse_contact_info(
        self, lines: List[Line], raw_text: str = ""
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        email = phone = name = None

        # Scan only up to the first section header — not a hardcoded line number
        stop = self._first_section_line(lines)
        contact_zone = lines[:stop]

        for line in contact_zone:
            if line.is_blank():
                continue
            if not email:
                tok = next((t.value for t in line.tokens if t.type == "EMAIL"), None)
                if tok:
                    email = tok
            if not phone:
                tok = self._pick_best_phone(line)
                if tok:
                    phone = tok

        # Fallbacks for cases where lexer fails (e.g. wrapped lines or unusual characters)
        if not email or not phone:
            if raw_text:
                orig_lines = raw_text.split('\n')
                raw_text_block = "\n".join(orig_lines[:stop])
            else:
                raw_text_block = "\n".join(l.raw for l in contact_zone)
            if not email:
                em_match = re.search(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', raw_text_block)
                if em_match:
                    email = em_match.group(0)
                else:
                    # Search allowing whitespace inside email pattern to capture line-wrapped emails.
                    # Uses non-greedy domain match ending with a common TLD and a word boundary to prevent swallowing extra characters.
                    em_match2 = re.search(
                        r'[a-zA-Z0-9._%+-]+\s*@\s*[a-zA-Z0-9.\s\-]+?\s*\.\s*(?:com|org|net|edu|gov|co|in|io|me|info|us|uk|ca|au|de|fr|[a-zA-Z]{2,4})\b',
                        raw_text_block,
                        flags=re.IGNORECASE
                    )
                    if em_match2:
                        email = re.sub(r'\s+', '', em_match2.group(0))

            if not phone:
                # Search line-by-line using local spaces to prevent merging zip codes and phones across lines
                for line in contact_zone:
                    ph_match = re.search(r'(?:\+?\d{1,3}[ \t.-]?)?\(?\d{2,4}\)?[ \t.-]?[\dXx]{3,10}[ \t.-]?[\dXx]{0,10}', line.raw)
                    if ph_match:
                        ph_str = ph_match.group(0).strip()
                        if sum(c.isdigit() or c.lower() == 'x' for c in ph_str) >= 7:
                            phone = ph_str
                            break

        # Name: first plausible non-contact line in the contact zone
        for line in contact_zone[:8]:
            if self._is_name_candidate(line):
                # Split by common separators (avoiding hyphen within words)
                name_parts = re.split(r'[|•·;/\\–—]|\s+-\s+', line.raw)
                name = re.sub(r'[,;]+$', '', name_parts[0]).strip()
                break

        return name, email, phone

    @staticmethod
    def _pick_best_phone(line: Line) -> Optional[str]:
        phones = [t.value for t in line.tokens if t.type == "PHONE"]
        if not phones:
            return None
        for p in phones:
            if p.startswith('+') or re.match(r'^(?:91|1)[\s\-]', p):
                return p
        return phones[0]