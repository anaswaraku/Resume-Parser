# parser.py

import nltk
import spacy
from nltk.corpus import stopwords
from typing import List, Optional
from lexer import Token
from ast_models import ResumeAST, Education, Experience


nltk.download('stopwords', quiet=True)
nlp = spacy.load("en_core_web_sm")
STOPWORDS = set(stopwords.words('english'))


SECTION_HEADERS = {
    'education':'EDUCATION',
    'experience':'EXPERIENCE',
    'work':'EXPERIENCE',
    'employment':'EXPERIENCE',
    'skills':'SKILLS',
    'technologies':'SKILLS',
    'summary':'SUMMARY',
    'objective':'SUMMARY',
    'certifications':'CERTIFICATIONS',
    'projects':'PROJECTS',
    }

class Parser:
    def __init__(self, tokens: List[Token], raw_text: str):
        self.tokens = tokens
        self.raw_text = raw_text
        self.pos = 0
        self.ast = ResumeAST()
        self.doc = nlp(raw_text)  # spaCy runs once on full text

    # ── Entry Point ───────────────────────────────────────────
    def parse(self) -> ResumeAST:
        self._extract_contact_info()  # Lexer tokens → email, phone
        self._extract_name()          # spaCy NER → PERSON
        self._parse_body()            # section by section
        return self.ast

    # ── 1. Contact Info (Lexer tokens) ────────────────────────
    def _extract_contact_info(self):
        for token in self.tokens:
            if token.type == 'EMAIL' and not self.ast.email:
                self.ast.email = token.value
            if token.type == 'PHONE' and not self.ast.phone:
                self.ast.phone = token.value

    # ── 2. Name (spaCy NER) ───────────────────────────────────
    def _extract_name(self):
        for ent in self.doc.ents:
            if ent.label_ == 'PERSON':
                self.ast.name = ent.text
                break  # first PERSON = candidate name

    # ── 3. Section Body ───────────────────────────────────────
    def _parse_body(self):
        while self.current():
            self._skip_newlines()
            t = self.current()
            if not t:
                break

            if self._is_section_header(t):
                section = SECTION_HEADERS[t.value.lower()]
                self.consume()
                self._skip_newlines()
                self._parse_section(section)
            else:
                self.consume()  # skip pre-section content

    def _parse_section(self, section: str):
        {
            'EDUCATION': self._parse_education,
            'EXPERIENCE': self._parse_experience,
            'SKILLS': self._parse_skills,
            'SUMMARY': self._parse_summary,
        }.get(section, self._skip_section)()

    # ── 4. Education ──────────────────────────────────────────
    def _parse_education(self):
        for line in self._collect_lines():
            dates = [t.value for t in line if t.type == 'DATE']
            words = [t.value for t in line if t.type == 'WORD']

            if not words:
                continue

            # spaCy finds university/college name
            line_doc = nlp(' '.join(t.value for t in line))
            school = next(
                (ent.text for ent in line_doc.ents if ent.label_ == 'ORG'),
                None
            )

            school_words = set(school.split()) if school else set()
            degree = ' '.join(w for w in words if w not in school_words)

            self.ast.education.append(
                Education(
                    degree=degree.strip() or None,
                    school=school,
                    start_date=dates[0] if len(dates) > 0 else None,
                    end_date=dates[1] if len(dates) > 1 else None,
                )
            )

    # ── 5. Experience ─────────────────────────────────────────
    def _parse_experience(self):
        for line in self._collect_lines():
            dates = [t.value for t in line if t.type == 'DATE']
            words = [t.value for t in line if t.type == 'WORD']

            if not words:
                continue

            # spaCy finds company name
            line_doc = nlp(' '.join(t.value for t in line))
            company = next(
                (ent.text for ent in line_doc.ents if ent.label_ == 'ORG'),
                None
            )

            company_words = set(company.split()) if company else set()
            role = ' '.join(w for w in words if w not in company_words)

            self.ast.experience.append(
                Experience(
                    company=company,
                    role=role.strip() or None,
                    start_date=dates[0] if len(dates) > 0 else None,
                    end_date=dates[1] if len(dates) > 1 else None,
                )
            )

    # ── 6. Skills ─────────────────────────────────────────────
    def _parse_skills(self):
        seen = set(self.ast.skills)

        for line in self._collect_lines():
            for token in line:
                if (
                    token.type == 'WORD'
                    and token.value.lower() not in STOPWORDS
                    and token.value not in seen
                    and len(token.value) > 1
                ):
                    self.ast.skills.append(token.value)
                    seen.add(token.value)

    # ── 7. Summary ────────────────────────────────────────────
    def _parse_summary(self):
        lines = self._collect_lines()
        words = [t.value for line in lines for t in line if t.type == 'WORD']
        self.ast.summary = ' '.join(words) or None

    # ── Helpers ───────────────────────────────────────────────
    def _collect_lines(self) -> List[List[Token]]:
        """Groups tokens into lines."""
        lines = []
        current_line = []

        while self.current() and not self._is_section_header(self.current()):
            t = self.current()

            if t.type == 'NEWLINE':
                if current_line:
                    lines.append(current_line)
                    current_line = []
                self.consume()
            else:
                current_line.append(self.consume())

        if current_line:
            lines.append(current_line)

        return lines

    def _is_section_header(self, token: Optional[Token]) -> bool:
        return (
            token is not None
            and token.type == 'WORD'
            and token.value.lower() in SECTION_HEADERS
        )

    def _skip_newlines(self):
        while self.current() and self.current().type == 'NEWLINE':
            self.consume()

    def _skip_section(self):
        self._collect_lines()  # discard unknown section

    def current(self) -> Optional[Token]:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def consume(self) -> Optional[Token]:
        t = self.current()
        self.pos += 1
        return t
    

txt = """RESUME

Name: Ananya Sharma  
Email: ananya.sharma@email.com  
Phone: +91 98765 43210  
Date of Birth: 15 March 2000  

----------------------------------------

Objective:
Motivated and detail-oriented individual seeking an entry-level position to utilize skills and grow professionally.

----------------------------------------

Education:
Bachelor of Science in Computer Science  
XYZ University, Kerala  
2021 – 2024  

Higher Secondary (12th Grade)  
ABC Higher Secondary School  
2019 – 2021  

Secondary School (10th Grade)  
ABC High School  
2018 – 2019  

----------------------------------------

Skills:
- Basic Programming (Python, Java)  
- MS Office (Word, Excel, PowerPoint)  
- Communication Skills  
- Teamwork and Problem Solving  

----------------------------------------

Experience:
Fresher

----------------------------------------

Declaration:
I hereby declare that the information provided above is true and correct to the best of my knowledge.

----------------------------------------

Place: Cochin  
Date: 22 June 2026  

Signature:  
Ananya Sharma"""

