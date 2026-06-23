"""
parser.py — Grammar-based Parser (Syntactic Analysis)

Consumes the token stream produced by the Lexer and builds a ResumeAST.

Educational concept: Top-Down / Recursive-Descent Parsing
  - The parser starts from high-level section headers and recurses downward.
  - It applies grammar rules, not just regex, to build hierarchical structure.
  - Handles missing / optional fields gracefully (returns None / empty lists).

Grammar (informal BNF):
    resume      ::= contact_block section*
    contact     ::= name? email? phone?
    section     ::= section_header entry+
    section_header ::= WORD  (where WORD ∈ SECTION_KEYWORDS)
    entry       ::= line+
    line        ::= token+ NEWLINE
"""

from typing import List, Optional, Dict, Set
from lexer import Token
from models import ResumeAST, Education, Experience


# ---------------------------------------------------------------------------
# Section-header keyword sets
# ---------------------------------------------------------------------------

EDUCATION_KEYWORDS: Set[str] = {
    "education", "academic", "academics", "qualification",
    "qualifications", "degree", "degrees", "study", "studies",
}

EXPERIENCE_KEYWORDS: Set[str] = {
    "experience", "employment", "work", "career", "history",
    "professional", "positions", "jobs",
}

SKILLS_KEYWORDS: Set[str] = {
    "skills", "skill", "technologies", "tools", "competencies",
    "expertise", "proficiencies", "technical",
}


# ---------------------------------------------------------------------------
# Helper dataclass — internal representation of a raw text section
# ---------------------------------------------------------------------------

class _Section:
    """Holds the header name and all tokens that belong to that section."""
    def __init__(self, header: str):
        self.header: str = header
        self.tokens: List[Token] = []
        self.lines: List[List[Token]] = []   # tokens grouped by NEWLINE

    def add_token(self, token: Token) -> None:
        self.tokens.append(token)

    def finalise_lines(self) -> None:
        """Group self.tokens into lines split on NEWLINE tokens."""
        current: List[Token] = []
        for tok in self.tokens:
            if tok.type == "NEWLINE":
                if current:
                    self.lines.append(current)
                    current = []
            else:
                current.append(tok)
        if current:
            self.lines.append(current)


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class Parser:
    """
    Applies grammar rules to a List[Token] and produces a ResumeAST.

    Usage
    -----
        from lexer import Lexer
        from parser import Parser

        tokens = Lexer().tokenize(resume_text)
        ast    = Parser(tokens).parse()
    """

    def __init__(self, tokens: List[Token]) -> None:
        self.tokens: List[Token] = tokens
        self._pos: int = 0          # current look-ahead pointer
        self._ast = ResumeAST()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse(self) -> ResumeAST:
        """
        Entry point.  Runs all sub-parsers and returns the populated AST.
        """
        self._extract_contact_info()
        sections = self._split_into_sections()
        for section in sections:
            header_lower = section.header.lower()
            if header_lower in EDUCATION_KEYWORDS:
                self._ast.education = self._parse_education(section)
            elif header_lower in EXPERIENCE_KEYWORDS:
                self._ast.experience = self._parse_experience(section)
            elif header_lower in SKILLS_KEYWORDS:
                self._ast.skills = self._parse_skills(section)
        return self._ast

    # ------------------------------------------------------------------
    # Contact info extraction — scans the WHOLE token stream
    # ------------------------------------------------------------------

    def _extract_contact_info(self) -> None:
        """
        Scan all tokens for EMAIL and PHONE patterns.
        Also attempts a naive name extraction from the very first WORD line.
        """
        name_candidates: List[str] = []
        collecting_name = True   # name heuristic: grab words from the first line

        for i, tok in enumerate(self.tokens):
            if tok.type == "EMAIL" and self._ast.email is None:
                self._ast.email = tok.value

            elif tok.type == "PHONE" and self._ast.phone is None:
                self._ast.phone = tok.value

            # Heuristic: the first non-empty line of WORD tokens is likely the name
            elif collecting_name:
                if tok.type == "WORD":
                    name_candidates.append(tok.value)
                elif tok.type == "NEWLINE":
                    if name_candidates:
                        # Stop after the first populated line
                        collecting_name = False
                        candidate = " ".join(name_candidates)
                        # Reject if it looks like a section keyword
                        if candidate.lower() not in (
                            EDUCATION_KEYWORDS | EXPERIENCE_KEYWORDS | SKILLS_KEYWORDS
                        ):
                            self._ast.name = candidate
                    # Empty newline — keep going until we hit words

    # ------------------------------------------------------------------
    # Section splitting
    # ------------------------------------------------------------------

    def _split_into_sections(self) -> List[_Section]:
        """
        Walk the token stream and group tokens under their nearest
        section header.  A "section header" is a WORD token whose
        lowercase value is in one of the keyword sets AND is the only
        (or first) meaningful token on its line.

        Returns a list of _Section objects in document order.
        """
        all_keywords = EDUCATION_KEYWORDS | EXPERIENCE_KEYWORDS | SKILLS_KEYWORDS
        sections: List[_Section] = []
        current_section: Optional[_Section] = None

        # Build lines first (split on NEWLINE)
        lines: List[List[Token]] = []
        line: List[Token] = []
        for tok in self.tokens:
            if tok.type == "NEWLINE":
                if line:
                    lines.append(line)
                line = []
            else:
                line.append(tok)
        if line:
            lines.append(line)

        for line_tokens in lines:
            # A section header line: first token is a keyword WORD,
            # optionally followed by a colon-like WORD.
            non_empty = [t for t in line_tokens if t.type != "NEWLINE"]
            if not non_empty:
                continue

            first = non_empty[0]
            if (first.type == "WORD"
                    and first.value.lower() in all_keywords
                    and len(non_empty) <= 2):          # "Education:" → 1-2 tokens
                # Start a new section
                current_section = _Section(header=first.value)
                sections.append(current_section)
            else:
                if current_section is not None:
                    for t in line_tokens:
                        current_section.add_token(t)
                    current_section.add_token(Token("NEWLINE", "\n", -1))

        for s in sections:
            s.finalise_lines()

        return sections

    # ------------------------------------------------------------------
    # Section parsers
    # ------------------------------------------------------------------

    def _parse_education(self, section: _Section) -> List[Education]:
        """
        Heuristic grammar for education entries:

            entry   ::= degree_line school_line? date_range?
            degree_line  ::= WORD+          (contains degree keywords like BSc/BA/MSc/PhD)
            school_line  ::= WORD+          (contains "University"/"College"/etc.)
            date_range   ::= DATE ('-'|'to'|'–') DATE

        Returns a list of Education objects.
        """
        entries: List[Education] = []

        degree_keywords = {"bsc", "ba", "bs", "msc", "ma", "ms", "mba",
                           "phd", "doctorate", "bachelor", "master",
                           "associate", "diploma", "certificate"}
        school_keywords = {"university", "college", "institute", "school",
                           "academy", "polytechnic"}

        # We accumulate raw lines and look for degree / school / date patterns
        current_degree: Optional[str] = None
        current_school: Optional[str] = None
        current_dates: List[str] = []

        def _flush() -> None:
            """Push the accumulated entry and reset accumulators."""
            nonlocal current_degree, current_school, current_dates
            if current_degree or current_school:
                edu = Education(
                    degree=current_degree,
                    school=current_school,
                    start_date=current_dates[0] if len(current_dates) > 0 else None,
                    end_date=current_dates[1] if len(current_dates) > 1 else None,
                )
                entries.append(edu)
            current_degree = None
            current_school = None
            current_dates = []

        for line_tokens in section.lines:
            words  = [t.value for t in line_tokens if t.type == "WORD"]
            dates  = [t.value for t in line_tokens if t.type == "DATE"]
            line_text = " ".join(t.value for t in line_tokens)

            if not words and not dates:
                continue

            lower_words = [w.lower() for w in words]

            # Does this line contain a degree keyword?
            has_degree = any(w in degree_keywords for w in lower_words)
            has_school = any(w in school_keywords for w in lower_words)

            if has_degree:
                if current_degree:   # new entry starts
                    _flush()
                current_degree = line_text
                if dates:
                    current_dates = dates
            elif has_school:
                current_school = line_text
                if dates:
                    current_dates = dates
            elif dates:
                current_dates = dates
            # else: skip unrecognised lines

        _flush()   # don't forget the last accumulated entry
        return entries

    def _parse_experience(self, section: _Section) -> List[Experience]:
        """
        Heuristic grammar for work-experience entries:

            entry       ::= company_line role_line? date_range? description*
            company_line::= WORD+    (first substantial line; may contain dates)
            role_line   ::= WORD+    (second line)
            date_range  ::= DATE ('-'|'to'|'–') DATE
            description ::= WORD+    (remaining lines)

        Returns a list of Experience objects.
        """
        entries: List[Experience] = []

        role_keywords = {"engineer", "developer", "manager", "director",
                         "analyst", "designer", "consultant", "lead",
                         "architect", "specialist", "intern", "associate",
                         "officer", "executive", "head", "vp", "president",
                         "coordinator", "scientist", "researcher"}

        current_company: Optional[str] = None
        current_role: Optional[str] = None
        current_dates: List[str] = []
        current_desc_lines: List[str] = []

        def _flush() -> None:
            nonlocal current_company, current_role, current_dates, current_desc_lines
            if current_company or current_role:
                exp = Experience(
                    company=current_company,
                    role=current_role,
                    start_date=current_dates[0] if len(current_dates) > 0 else None,
                    end_date=current_dates[1] if len(current_dates) > 1 else None,
                    description=" | ".join(current_desc_lines) or None,
                )
                entries.append(exp)
            current_company = None
            current_role = None
            current_dates = []
            current_desc_lines = []

        # State machine: 'company' → 'role' → 'desc'
        state = "company"

        for line_tokens in section.lines:
            words = [t.value for t in line_tokens if t.type == "WORD"]
            dates = [t.value for t in line_tokens if t.type == "DATE"]
            line_text = " ".join(t.value for t in line_tokens)

            if not words and not dates:
                continue

            lower_words = [w.lower() for w in words]
            has_role = any(w in role_keywords for w in lower_words)

            if state == "company":
                current_company = line_text
                if dates:
                    current_dates = dates
                state = "role"
            elif state == "role":
                if has_role:
                    current_role = line_text
                    if dates:
                        current_dates = dates
                    state = "desc"
                elif dates:
                    # A date-only line right after company → capture dates
                    if not current_dates:
                        current_dates = dates
                    state = "desc"
                else:
                    # Treat as description already
                    current_desc_lines.append(line_text)
                    state = "desc"
            else:  # desc
                # Detect start of a new experience entry:
                # short line (≤5 words), starts with uppercase, no dates, no role keyword
                is_new_entry = (
                    not has_role
                    and not dates
                    and len(words) >= 1
                    and len(words) <= 5
                    and words[0][0].isupper()
                    and current_company is not None
                    and not current_desc_lines   # nothing accumulated yet → more likely new entry
                )
                # A date-range line (contains dates but few or no WORD tokens)
                is_date_line = dates and len(words) <= 4

                if is_date_line and not current_dates:
                    current_dates = dates
                elif is_new_entry:
                    _flush()
                    current_company = line_text
                    state = "role"
                else:
                    current_desc_lines.append(line_text)

        _flush()
        return entries

    def _parse_skills(self, section: _Section) -> List[str]:
        """
        Collect all WORD tokens from the Skills section.

        Because the Lexer strips punctuation (commas, pipes, slashes), each
        WORD token on a skills line is already an individual skill candidate.
        We treat every WORD token as its own skill entry and deduplicate.

        Multi-word skills (e.g. "Machine Learning") are handled by grouping
        consecutive WORD tokens that appear on the same line without an
        intervening punctuation gap — here we keep them as individual words
        since we can't recover commas the lexer discarded. Users who want
        multi-word skills should use the LLM parser module.
        """
        skills: Set[str] = set()

        for line_tokens in section.lines:
            for tok in line_tokens:
                if tok.type == "WORD" and len(tok.value) > 1:
                    skills.add(tok.value)

        return sorted(skills)

"""
lexer.py — Tokenizer (Lexical Analysis)

Converts raw resume text into a flat stream of typed Token objects.
Token types: EMAIL, PHONE, DATE, NUMBER, NEWLINE, WORD

Educational concept: Lexical Analysis
  - The lexer is the first stage of a compiler/parser pipeline.
  - It reads raw characters and groups them into meaningful units (tokens).
  - Grammar rules are NOT applied here — only pattern matching.
"""

import re
from dataclasses import dataclass
from typing import List, Tuple, Optional


# ---------------------------------------------------------------------------
# Token dataclass
# ---------------------------------------------------------------------------

@dataclass
class Token:
    """A single lexical unit produced by the Lexer."""
    type: str       # e.g. 'EMAIL', 'PHONE', 'DATE', 'WORD', 'NUMBER', 'NEWLINE'
    value: str      # the matched text
    position: int   # character offset in the original string (useful for debugging)

    def __repr__(self) -> str:
        return f"Token({self.type}, {self.value!r}, pos={self.position})"


# ---------------------------------------------------------------------------
# Lexer
# ---------------------------------------------------------------------------

class Lexer:
    """
    Tokenizes plain-text resume content into a List[Token].

    TOKEN_PATTERNS is an ordered list of (token_type, regex) pairs.
    Order matters: more-specific patterns must appear before catch-all ones.
    The lexer tries each pattern at the current position and advances past
    the first match, skipping whitespace between tokens.
    """

    # (token_type, compiled_regex) — order is significant
    TOKEN_PATTERNS: List[Tuple[str, re.Pattern]] = [
        # EMAIL must come before WORD to avoid partial matches
        ("EMAIL",   re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b')),
        # PHONE: handles 123-456-7890, 123.456.7890, 1234567890
        ("PHONE",   re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b')),
        # DATE: "Jan 2020", "Mar 2024", etc.
        ("DATE",    re.compile(
            r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s*\d{4}\b',
            re.IGNORECASE
        )),
        # Bare 4-digit years
        ("NUMBER",  re.compile(r'\b\d{4}\b')),
        # Generic numbers (must come after NUMBER so 4-digit years are caught first)
        ("NUMBER",  re.compile(r'\b\d+\b')),
        # Newline — tracked so the parser can use line boundaries
        ("NEWLINE", re.compile(r'\n')),
        # Any word (letters, hyphens, apostrophes)  — catch-all
        ("WORD",    re.compile(r"[A-Za-z][A-Za-z'\-]*")),
    ]

    # Whitespace pattern used to skip spaces/tabs between tokens
    _SKIP = re.compile(r'[ \t\r]+')

    def tokenize(self, text: str) -> List[Token]:
        """
        Convert *text* into a list of Token objects.

        Parameters
        ----------
        text : str
            Raw text extracted from the resume file.

        Returns
        -------
        List[Token]
            Ordered list of tokens; NEWLINE tokens are included so the
            parser can detect line breaks without counting characters.
        """
        tokens: List[Token] = []
        pos = 0
        length = len(text)

        while pos < length:
            # Skip horizontal whitespace
            skip_match = self._SKIP.match(text, pos)
            if skip_match:
                pos = skip_match.end()
                continue

            matched = False
            for token_type, pattern in self.TOKEN_PATTERNS:
                m = pattern.match(text, pos)
                if m:
                    tokens.append(Token(type=token_type, value=m.group(), position=pos))
                    pos = m.end()
                    matched = True
                    break

            if not matched:
                # Unknown character — skip it (punctuation, special chars, etc.)
                pos += 1

        return tokens

"""
main.py — FastAPI Application (Traditional Parser only)

Endpoint:
    POST /parse-resume-hybrid
        Accepts a resume file upload (PDF, DOCX, TXT, RTF).
        Runs the traditional (Lexer → Parser → AST) pipeline.
        Returns structured JSON matching FR-10 output schema.

Run:
    uvicorn main:app --reload --host 0.0.0.0 --port 8000

Docs:
    http://localhost:8000/docs
"""

import os
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from models import ResumeAST
from lexer import Lexer
from parser import Parser
from utils.file_extractor import (
    extract_text_from_docx,
    extract_text_from_pdf,
    extract_text_from_txt,
)

# ---------------------------------------------------------------------------
# Configuration (mirrors .env values; override via real .env + python-dotenv)
# ---------------------------------------------------------------------------

MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", 10 * 1024 * 1024))   # 10 MB
SUPPORTED_EXTENSIONS: set[str] = {".pdf", ".docx", ".txt", ".rtf"}
REJECTED_EXTENSIONS: set[str] = {".exe", ".bat", ".sh", ".cmd", ".ps1"}

# ---------------------------------------------------------------------------
# Response schema (FR-10)
# ---------------------------------------------------------------------------

class ParseResponse(BaseModel):
    traditional_parser: ResumeAST
    llm_parser: Optional[ResumeAST] = None        # always None here (no LLM)
    merged_result: ResumeAST
    parsing_method: str = "traditional_only"

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Hybrid Resume Parser API (Traditional)",
    description=(
        "Educational project demonstrating Lexical Analysis → Syntactic Parsing → AST. "
        "LLM integration is disabled in this traditional-only build."
    ),
    version="1.0.0",
)


@app.get("/", summary="Health check")
async def root():
    return {"status": "ok", "message": "Resume Parser API is running."}


@app.post(
    "/parse-resume-hybrid",
    response_model=ParseResponse,
    summary="Parse a resume file using the traditional parser",
    responses={
        400: {"description": "Invalid file (bad format, too large, unsupported extension)"},
        500: {"description": "Internal parsing error"},
    },
)
async def parse_resume_hybrid(
    file: UploadFile = File(..., description="Resume file (PDF, DOCX, TXT, RTF)"),
    use_llm: bool = Query(
        default=False,
        description="Set true to enable LLM parsing (not implemented in this build)",
    ),
) -> ParseResponse:
    """
    Main parsing endpoint.

    1. Validates file size and extension.
    2. Saves the upload to a temporary file.
    3. Extracts plain text via the appropriate extractor.
    4. Runs Lexer → Parser → ResumeAST.
    5. Returns the structured result.
    """

    # ── 1. Security: reject executable extensions ──────────────────────────
    suffix = Path(file.filename or "").suffix.lower()
    if suffix in REJECTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Executable file type not allowed: {suffix}",
        )

    # ── 2. Validate extension ───────────────────────────────────────────────
    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format: {suffix or '(none)'}",
        )

    # ── 3. Read & size-check ────────────────────────────────────────────────
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail="File size exceeds 10MB limit",
        )

    # ── 4. Save to temp file (extractors need a file path) ──────────────────
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    # ── 5. Text extraction ──────────────────────────────────────────────────
    try:
        if suffix == ".pdf":
            resume_text = extract_text_from_pdf(tmp_path)
        elif suffix == ".docx":
            resume_text = extract_text_from_docx(tmp_path)
        else:   # .txt or .rtf
            resume_text = extract_text_from_txt(tmp_path)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=f"Failed to extract text from file: {exc}")
    finally:
        os.unlink(tmp_path)   # always clean up the temp file

    if not resume_text.strip():
        raise HTTPException(status_code=400, detail="File appears to be empty or unreadable.")

    # ── 6. Traditional parsing pipeline ─────────────────────────────────────
    try:
        tokens = Lexer().tokenize(resume_text)
        traditional_result: ResumeAST = Parser(tokens).parse()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Traditional parser error: {exc}")

    # ── 7. LLM note ─────────────────────────────────────────────────────────
    if use_llm:
        # Placeholder — LLM integration is a separate module (llm_parser.py)
        # In this traditional-only build we log and continue without it.
        print("[INFO] use_llm=true requested but LLM parser is not enabled in this build.")

    # ── 8. Build response (merged == traditional when no LLM) ───────────────
    return ParseResponse(
        traditional_parser=traditional_result,
        llm_parser=None,
        merged_result=traditional_result,
        parsing_method="traditional_only",
    )

"""
utils/file_extractor.py — Text Extraction from Binary Resume Formats

Supported formats: PDF, DOCX, TXT, RTF

Each function accepts a file path string and returns plain text.
Encoding errors are handled with a UTF-8 fallback to latin-1.
"""

import re


def extract_text_from_pdf(filepath: str) -> str:
    """
    Extract plain text from a PDF file using pdfplumber.
    Preserves paragraph structure by joining lines within a page
    and separating pages with double newlines.

    Parameters
    ----------
    filepath : str
        Absolute or relative path to the PDF file.

    Returns
    -------
    str
        Extracted plain text.

    Raises
    ------
    RuntimeError
        If pdfplumber cannot open or read the file.
    """
    try:
        import pdfplumber
    except ImportError:
        raise RuntimeError(
            "pdfplumber is not installed. Run: pip install pdfplumber"
        )

    pages: list[str] = []
    try:
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages.append(text.strip())
    except Exception as exc:
        raise RuntimeError(f"Failed to extract text from PDF: {exc}") from exc

    return "\n\n".join(pages)


def extract_text_from_docx(filepath: str) -> str:
    """
    Extract plain text from a DOCX file using python-docx.
    Each paragraph is returned on its own line.

    Parameters
    ----------
    filepath : str
        Path to the .docx file.

    Returns
    -------
    str
        Extracted plain text.

    Raises
    ------
    RuntimeError
        If python-docx cannot open or read the file.
    """
    try:
        from docx import Document
    except ImportError:
        raise RuntimeError(
            "python-docx is not installed. Run: pip install python-docx"
        )

    try:
        doc = Document(filepath)
        lines = [para.text for para in doc.paragraphs if para.text.strip()]
        return "\n".join(lines)
    except Exception as exc:
        raise RuntimeError(f"Failed to extract text from DOCX: {exc}") from exc


def extract_text_from_txt(filepath: str) -> str:
    """
    Read a plain-text or RTF file and return its contents.

    For RTF files a lightweight tag-stripping regex is applied so that
    the parser receives clean text rather than RTF control words.

    Parameters
    ----------
    filepath : str
        Path to the .txt or .rtf file.

    Returns
    -------
    str
        Raw (or stripped) text content.

    Raises
    ------
    RuntimeError
        If the file cannot be read.
    """
    try:
        with open(filepath, "r", encoding="utf-8") as fh:
            content = fh.read()
    except UnicodeDecodeError:
        try:
            with open(filepath, "r", encoding="latin-1") as fh:
                content = fh.read()
        except Exception as exc:
            raise RuntimeError(f"Failed to read file with latin-1 encoding: {exc}") from exc
    except Exception as exc:
        raise RuntimeError(f"Failed to read file: {exc}") from exc

    # Lightweight RTF stripping (handles basic RTF documents)
    if filepath.lower().endswith(".rtf"):
        content = _strip_rtf(content)

    return content


def _strip_rtf(rtf_text: str) -> str:
    """
    Remove RTF control words and braces, leaving plain text.
    This is a best-effort implementation suitable for typical resumes.
    For complex RTF documents consider the `striprtf` package.
    """
    # Remove RTF groups and control words
    text = re.sub(r'\{[^{}]*\}', ' ', rtf_text)          # remove braces groups
    text = re.sub(r'\\[a-z]+\-?\d*\s?', ' ', text)       # remove control words
    text = re.sub(r'\\[\\\{\}]', '', text)                # remove escaped chars
    text = re.sub(r'[{}]', ' ', text)                     # remove remaining braces
    text = re.sub(r'\s+', ' ', text).strip()
    return text