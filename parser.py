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

Grammar (informal BNF):
    resume       ::= contact section*
    contact      ::= name? email? phone?
    section      ::= section_header entry+
    entry        ::= field+
    field        ::= TOKEN+

The parser is truly hierarchical because:
  1. It first identifies the top-level section boundaries.
  2. Then recurses into each section to identify entry boundaries.
  3. Then recurses into each entry to extract individual fields.
Each level only knows about its own grammar rule.
"""

from typing import List, Optional, Set
from lexer import Token
from ast_models import ResumeAST, Education, Experience


#/Section keyword 

EDU_KW   = {"education","academic","academics","qualification","qualifications","degree","study","studies","schooling"}
EXP_KW   = {"experience","employment","work","career","history","professional","positions","jobs","internship","internships"}
SKILL_KW = {"skills","skill","technologies","tools","competencies","expertise","proficiencies","technical","stack","languages","frameworks"}
ALL_KW   = EDU_KW | EXP_KW | SKILL_KW

#/Degree vocabulary 

_DEG_ABBREV = {"bsc","ba","bs","beng","btech","msc","ma","ms","meng","mtech",
               "mba","phd","dphil","edd","associate","diploma","certificate","hnd"}
_DEG_START  = {"bachelor","master","doctor","doctorate"}
_DEG_NEXT   = {"of","in","science","arts","engineering","technology","business","commerce"}

#/Role vocabulary/

_ROLE_KW = {"engineer","developer","manager","director","analyst","designer",
            "consultant","lead","architect","specialist","intern","associate",
            "officer","executive","head","vp","president","coordinator",
            "scientist","researcher","founder","cto","ceo","coo","cfo","senior","junior"}

#/School vocabulary

_SCHOOL_KW = {"university","college","institute","school","academy","polytechnic","iit","mit","bits"}


#/Internal node: a named group of token-lines ────────────────────────────

class _SectionNode:
    """
    Intermediate AST node representing one resume section.
    Holds the parsed lines that belong to it; consumed by section parsers.
    """
    __slots__ = ("name", "lines")

    def __init__(self, name: str):
        self.name  = name
        self.lines: List[List[Token]] = []


#/Helpers/────────

def _words(line):   return [t.value for t in line if t.type == "WORD"]
def _dates(line):   return [t.value for t in line if t.type == "DATE"]
def _text(line):
    out, prev_sep = [], False
    for t in line:
        if t.type == "SEPARATOR":
            prev_sep = True
        elif t.type != "NEWLINE":
            if out and not prev_sep:
                out.append(" ")
            out.append(t.value)
            prev_sep = False
    return "".join(out).strip()

def _has_degree(words):
    low = [w.lower() for w in words]
    if any(w in _DEG_ABBREV for w in low):
        return True
    for i, w in enumerate(low):
        if w in _DEG_START and i+1 < len(low) and low[i+1] in _DEG_NEXT:
            return True
    return False

def _has_role(words):
    return any(w.lower() in _ROLE_KW for w in words)

def _has_school(words):
    return any(w.lower() in _SCHOOL_KW for w in words)


#/Parser/─────────

class Parser:

    def __init__(self, tokens: List[Token]):
        self._tokens = tokens
        self._lines  = self._build_lines()

    #/Public/──────

    def parse(self) -> ResumeAST:
        """
        Top-level parse call.  Three recursive stages:
          1. _parse_contact()   — scans full token stream for contact fields
          2. _parse_sections()  — splits stream into _SectionNode objects
          3. _parse_<type>()    — recurses into each section to build entries
        """
        ast = ResumeAST()
        ast.name,  ast.email, ast.phone = self._parse_contact()
        for section in self._parse_sections():
            key = section.name
            if key in EDU_KW:
                ast.education  = self._parse_education(section)
            elif key in EXP_KW:
                ast.experience = self._parse_experience(section)
            elif key in SKILL_KW:
                ast.skills     = self._parse_skills(section)
        return ast

    #/Stage 0: build line list (single pass, shared) ──────────────────────

    def _build_lines(self) -> List[List[Token]]:
        lines, cur = [], []
        for tok in self._tokens:
            if tok.type == "NEWLINE":
                lines.append(cur)
                cur = []
            else:
                cur.append(tok)
        if cur:
            lines.append(cur)
        return lines

    #/Stage 1: contact parsing ─────────────────────────────────────────────

    def _parse_contact(self):
        """
        Scans the full token stream.
        Name: scored heuristic over the first 8 non-empty lines.
          +2 for 2-4 Title-Case WORD tokens
          +1 if all words are Title-Cased
          -5 if first word is a section/role keyword
          disqualified if line contains EMAIL/PHONE/URL/NUMBER
        """
        email = phone = None
        for tok in self._tokens:
            if tok.type == "EMAIL" and not email:
                email = tok.value
            elif tok.type == "PHONE" and not phone:
                phone = tok.value

        name, best = None, -99
        checked = 0
        for line in self._lines:
            if not line: continue
            checked += 1
            if checked > 8: break
            types = {t.type for t in line}
            if types & {"EMAIL","PHONE","URL","NUMBER"}: continue
            ws = _words(line)
            if not ws: continue
            score  = 2 if 2 <= len(ws) <= 4 else 0
            score += 1 if all(w[0].isupper() for w in ws) else 0
            score -= 5 if ws[0].lower() in ALL_KW else 0
            score -= 3 if ws[0].lower() in _ROLE_KW else 0
            if score > best:
                best, name = score, " ".join(ws)

        return (name if best >= 2 else None), email, phone

    #/Stage 2: section splitting ────────────────────────────────────────────

    def _parse_sections(self) -> List[_SectionNode]:
        """
        Identifies section headers and groups subsequent lines under them.
        A line is a header when its first token is a keyword WORD and
        the line contains ≤ 3 tokens total (avoids grabbing content lines
        that happen to start with a keyword).
        """
        sections: List[_SectionNode] = []
        current: Optional[_SectionNode] = None

        for line in self._lines:
            non_empty = [t for t in line if t.type != "NEWLINE"]
            if not non_empty:
                continue
            first = non_empty[0]
            is_header = (
                first.type == "WORD"
                and first.value.lower() in ALL_KW
                and len(non_empty) <= 3
            )
            if is_header:
                current = _SectionNode(first.value.lower())
                sections.append(current)
            elif current:
                current.lines.append(line)

        return sections

    #/Stage 3a: education ───────────────────────────────────────────────────

    def _parse_education(self, section: _SectionNode) -> List[Education]:
        """
        Hierarchical entry detection:
          For each line, classify it as: degree | school | date | other.
          A new degree line signals a new entry → flush the previous one.

        Entry grammar:
            education_entry ::= degree_line school_line? date_line?
        """
        entries = []
        cur_degree = cur_school = None
        cur_dates: List[str] = []

        def flush():
            nonlocal cur_degree, cur_school, cur_dates
            if cur_degree or cur_school:
                entries.append(Education(
                    degree=cur_degree, school=cur_school,
                    start_date=cur_dates[0] if len(cur_dates) > 0 else None,
                    end_date  =cur_dates[1] if len(cur_dates) > 1 else None,
                ))
            cur_degree = cur_school = None
            cur_dates = []

        for line in section.lines:
            ws, ds = _words(line), _dates(line)
            if not ws and not ds: continue
            if _has_degree(ws):
                if cur_degree: flush()          # new entry starts
                cur_degree = _text(line)
                if ds: cur_dates = ds
            elif _has_school(ws):
                cur_school = _text(line)
                if ds: cur_dates = ds
            elif ds:
                cur_dates = ds

        flush()
        return entries

    #/Stage 3b: experience ──────────────────────────────────────────────────

    def _parse_experience(self, section: _SectionNode) -> List[Experience]:
        """
        Hierarchical entry detection with look-ahead:
          Each entry = company → role → dates → description lines.
          A new company is detected by peeking at the next line — if it
          contains a role keyword or date, the current line is a new company.

        Entry grammar:
            experience_entry ::= company_line role_line? date_line? desc_line*
        """
        entries = []
        cur_company = cur_role = None
        cur_dates: List[str] = []
        cur_desc: List[str] = []

        def flush():
            nonlocal cur_company, cur_role, cur_dates, cur_desc
            if cur_company or cur_role:
                entries.append(Experience(
                    company    = cur_company,
                    role       = cur_role,
                    start_date = cur_dates[0] if len(cur_dates) > 0 else None,
                    end_date   = cur_dates[1] if len(cur_dates) > 1 else None,
                    description= ". ".join(cur_desc) or None,
                ))
            cur_company = cur_role = None
            cur_dates = []
            cur_desc = []

        active = [ln for ln in section.lines if ln]

        state = "start"
        for idx, line in enumerate(active):
            ws, ds, txt = _words(line), _dates(line), _text(line)
            if not ws and not ds: continue

            # date-only lines (≤4 words + has dates)
            if ds and len(ws) <= 4:
                if not cur_dates: cur_dates = ds
                continue

            # role line
            if _has_role(ws) and state in ("start", "company", "role"):
                cur_role = txt
                state = "desc"
                continue

            # look-ahead: short Title-Case line while in desc/role state
            # → peek next line; if it has a role/date, this is a new company
            if state in ("desc", "role") and 1 <= len(ws) <= 5 and ws[0][0].isupper() and not ds:
                next_line = active[idx+1] if idx+1 < len(active) else []
                nw = _words(next_line)
                nd = _dates(next_line)
                if _has_role(nw) or nd:
                    flush()
                    cur_company = txt
                    state = "role"
                    continue

            # first line = company
            if state in ("start", "company"):
                cur_company = txt
                state = "role"
            else:
                cur_desc.append(txt)

        flush()
        return entries

    #/Stage 3c: skills ──────────────────────────────────────────────────────

    def _parse_skills(self, section: _SectionNode) -> List[str]:
        """
        SEPARATOR tokens from the Lexer act as explicit boundaries.
        Consecutive WORD tokens between separators = one multi-word skill.
        e.g. "Machine Learning, Python" → ["Machine Learning", "Python"]
        """
        skills: List[str] = []
        seen: Set[str] = set()
        buf: List[str] = []

        def flush():
            skill = " ".join(buf).strip()
            if skill and len(skill) > 1 and skill.lower() not in seen:
                seen.add(skill.lower())
                skills.append(skill)
            buf.clear()

        for line in section.lines:
            for tok in line:
                if tok.type == "WORD":
                    buf.append(tok.value)
                elif tok.type == "SEPARATOR":
                    flush()
            flush()  # end of line

        return sorted(skills)