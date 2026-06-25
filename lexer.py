import re
from dataclasses import dataclass
from typing import List, Tuple

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
        # Range with full month names: "January 2020 - March 2024" or "Jan 2020 – Present"
        ('DATE_RANGE',
         re.compile(r'\b(?:January|February|March|April|May|June|July|August|September|'
         r'October|November|December|'
         r'Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)'
         r'\.?\s+\d{4}'
         r'\s*[-–—to]+\s*'
         r'(?:January|February|March|April|May|June|July|August|September|'
         r'October|November|December|'
         r'Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec'
         r'\.?\s+\d{4}|[Pp]resent|[Cc]urrent|[Nn]ow)')),
        # Year range: "2021 – 2024" or "2021 - Present"
        ('YEAR_RANGE',
         re.compile(r'\b(19|20)\d{2}\s*[-–—to]+\s*(?:(19|20)\d{2}|[Pp]resent|[Cc]urrent)\b')),
        # Single month+year: "Jun 2020" or "June 2020"
        ('DATE',
         re.compile(r'\b(?:January|February|March|April|May|June|July|August|September|'
         r'October|November|December|'
         r'Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)'
         r'\.?\s+\d{4}\b')),
        # Day Month Year: "22 June 2026" or "15 March 2000"
        ('DATE_DMY',
         re.compile(r'\b\d{1,2}\s+'
         r'(?:January|February|March|April|May|June|July|August|September|'
         r'October|November|December|'
         r'Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)'
         r'\s+\d{4}\b')),
        # Standalone year
        ('YEAR',
         re.compile(r'\b(19|20)\d{2}\b')),
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