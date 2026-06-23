# Tokenizer implementation
# Tokenize raw text into EMAIL, PHONE, DATE, WORD tokens
# lexer.py

import re
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Token:#token objevt 
    type:str
    value:str
    position:int

class Lexer:
    """Converts raw text to tokens"""
    TOKEN_PATTERNS = [
        ('EMAIL',
         r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'),
        # Handles: +91 98765 43210 | +1-800-555-1234 | (123) 456-7890 | 123.456.7890
        ('PHONE',
         r'\+\d{1,3}[\s.\-]?\d{4,5}[\s.\-]?\d{4,5}'   # +91 98765 43210
         r'|(\(?\d{3}\)?[\s.\-]?\d{3}[\s.\-]?\d{4})'), # (123) 456-7890
        ('URL',
         r'https?://[^\s]+|www\.[^\s]+'
         r'|linkedin\.com/in/[^\s]+'
         r'|github\.com/[^\s]+'),
        # ── Dates — most specific first ───────────────────────
        # Range with full month names: "January 2020 - March 2024" or "Jan 2020 – Present"
        ('DATE_RANGE',
         r'\b(?:January|February|March|April|May|June|July|August|September|'
         r'October|November|December|'
         r'Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)'
         r'\.?\s+\d{4}'
         r'\s*[-–—to]+\s*'
         r'(?:January|February|March|April|May|June|July|August|September|'
         r'October|November|December|'
         r'Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec'
         r'\.?\s+\d{4}|[Pp]resent|[Cc]urrent|[Nn]ow)'),
        # Year range: "2021 – 2024" or "2021 - Present"
        ('YEAR_RANGE',
         r'\b(19|20)\d{2}\s*[-–—to]+\s*(?:(19|20)\d{2}|[Pp]resent|[Cc]urrent)\b'),
        # Single month+year: "Jun 2020" or "June 2020"
        ('DATE',
         r'\b(?:January|February|March|April|May|June|July|August|September|'
         r'October|November|December|'
         r'Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)'
         r'\.?\s+\d{4}\b'),
        # Day Month Year: "22 June 2026" or "15 March 2000"
        ('DATE_DMY',
         r'\b\d{1,2}\s+'
         r'(?:January|February|March|April|May|June|July|August|September|'
         r'October|November|December|'
         r'Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)'
         r'\s+\d{4}\b'),
        # Standalone year
        ('YEAR',
         r'\b(19|20)\d{2}\b'),
        # ── Structure ─────────────────────────────────────────
        ('NEWLINE',   r'\n'),
        ('SEPARATOR', r'[|•·,;/\\]'),
        ('SKIP',      r'[ \t\r]+'),     # horizontal whitespace — drop
        # ── Catch-all — must be last ──────────────────────────
        ('WORD',      r"[A-Za-z0-9_.'\-]+"),
    
    ]
    def __init__(self):
        self.master_pattern =  re.compile(#create a large regex containing all token patterns using regex OR operator EMAIL_REGEX|PHONE_REGEX|.......
            '|'.join(f'(?P<{name}>{pattern})'#named caputer group
                     for name, pattern in self.TOKEN_PATTERNS)
        )

    def tokenize(self, text:str)->List[Token]:
        tokens=[]
        for match in self.master_pattern.finditer(text):
            token_type = match.lastgroup
            if token_type=='SKIP':
                continue
            tokens.append(Token(
                type=token_type,
                value=match.group(),
                position=match.start()
            ))
        return tokens#Token(type='WORD', value='Cochin', position=1023)

