import re
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class Token:
    type: str
    value: str
    position: int

    def __repr__(self):
        return f"Token({self.type}, {self.value!r})"


class Lexer:
    """
    Stage 1 — Lexical Analysis.
    Reads raw characters, groups them into typed tokens.
    No structure or grammar applied here — just pattern matching.
    """

    TOKEN_PATTERNS: List[Tuple[str, re.Pattern]] = [
        # URL before EMAIL — emails appear inside URLs
        ("URL",       re.compile(r'https?://\S+|(?:www\.|linkedin\.com|github\.com)\S+', re.I)),
        # EMAIL
        ("EMAIL",     re.compile(r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b')),
        # PHONE — dashes, dots, spaces, optional country code, parens
        ("PHONE",     re.compile(r'(?:\+\d{1,3}[\s\-]?)?(?:\(?\d{3}\)?[\s\-.]?)\d{3}[\s\-.]?\d{4}\b')),
        # DATE — "Jan 2020", "January 2020", "01/2020", "Present"
        ("DATE",      re.compile(
            r'\b(?:Present|Current|Now)\b'
            r'|(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?'
            r'|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'
            r'\.?\s*\d{4}'
            r'|\b(?:0?[1-9]|1[0-2])/\d{4}\b',
            re.I,
        )),
        # 4-digit year (standalone)
        ("NUMBER",    re.compile(r'\b\d{4}\b')),
        # Any other integer
        ("NUMBER",    re.compile(r'\b\d+\b')),
        # Separators — emitted so parser can split multi-word skills
        ("SEPARATOR", re.compile(r'[,|;•·]')),
        # Newline — section boundary signal
        ("NEWLINE",   re.compile(r'\n')),
        # Word — letters, hyphens, apostrophes, dots (for "Node.js", "C++")
        ("WORD",      re.compile(r"[A-Za-z][A-Za-z0-9'.+#\-]*")),
    ]

    _SKIP = re.compile(r'[ \t\r]+')

    def tokenize(self, text: str) -> List[Token]:
        tokens, pos = [], 0
        while pos < len(text):
            if m := self._SKIP.match(text, pos):
                pos = m.end()
                continue
            for ttype, pattern in self.TOKEN_PATTERNS:
                if m := pattern.match(text, pos):
                    tokens.append(Token(ttype, m.group(), pos))
                    pos = m.end()
                    break
            else:
                pos += 1  # skip unknown character
        return tokens