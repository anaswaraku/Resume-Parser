import re
from dataclasses import dataclass
from typing import List, Tuple


_MONTH = r'(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec|0?[1-9]|1[0-2])'
_YEAR = r'(?:19|20)\d{2}'
_SEP = r'[\s\-/\.,]+'
_RANGE_SEP = r'[\s\-–—to]+'
_PRESENT = r'(?:present|current|now)'

# (?i) makes them case-insensitive so "may", "MAY", "May" all match.
_DATE = fr'(?i)\b{_MONTH}\.?{_SEP}{_YEAR}\b'
_DATE_DMY = fr'(?i)\b\d{{1,2}}{_SEP}{_MONTH}\.?{_SEP}{_YEAR}\b'
_DATE_RANGE = fr'(?i)\b{_MONTH}\.?{_SEP}{_YEAR}{_RANGE_SEP}(?:{_MONTH}\.?{_SEP}{_YEAR}|{_PRESENT})\b'
_YEAR_RANGE = fr'(?i)\b{_YEAR}{_RANGE_SEP}(?:{_YEAR}|\d{{2}}|{_PRESENT})\b'

#automatically creates constructors and utility methods
@dataclass
class Token:
    type: str
    value: str
    position: int

    def __repr__(self):#define how object prints
        return f"Token({self.type}, {self.value!r})"


class Lexer:
    """
    Lexical Analysis.
    Reads raw characters, groups them into typed tokens.
    pattern matching.
    """

    TOKEN_PATTERNS: List[Tuple[str, re.Pattern]] = [
        ('EMAIL', re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b')),
            # Handles: +91 98765 43210 | +1-800-555-1234 | (123) 456-7890 | 123.456.7890
        ('PHONE',
         re.compile(r'\+\d{1,3}[\s.\-]?\d{4,5}[\s.\-]?\d{4,5}'   # +91 98765 43210
         r'|(\(?\d{3}\)?[\s.\-]?\d{3}[\s.\-]?\d{4})')), # (123) 456-7890
        ('URL',
        re.compile( r'https?://[^\s]+|www\.[^\s]+'
         r'|linkedin\.com/in/[^\s]+'
         r'|github\.com/[^\s]+')),
        #Dates — most specific first 
        ('DATE_RANGE', re.compile(_DATE_RANGE)),
        ('YEAR_RANGE', re.compile(_YEAR_RANGE)),
        ('DATE_DMY',   re.compile(_DATE_DMY)),
        ('DATE',       re.compile(_DATE)),
        # Standalone year
        ('YEAR',       re.compile(fr'\b{_YEAR}\b')),
        ('DATE_PRESENT',re.compile(fr'(?i)\b{_PRESENT}\b') ),
        #Structure
        ('NEWLINE',  re.compile( r'\n')),
        ('SEPARATOR', re.compile(r'[|•·,;/\\]')),
        ('SKIP',re.compile(r'[ \t\r]+')),     # horizontal whitespace — drop
        #Catch-all — must be last 
        ('WORD', re.compile(r"[A-Za-z0-9_.'\-]+")),]

    _SKIP = re.compile(r'[ \t\r]+')#white space-spaces,tabs - discard

    #text to tokens
    def tokenize(self, text: str) -> List[Token]:
        """Returns tokens as list of dictionary"""
        tokens, pos = [], 0#tracks current character position
        while pos < len(text):#at each position try every patter in order and take first match
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
        return tokens#return matched substring