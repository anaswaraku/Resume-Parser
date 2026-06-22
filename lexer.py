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
        ('EMAIL',   r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'),
        ('PHONE',   r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'),
        ('DATE',    r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s*\d{4}\b'),
        ('YEAR',    r'\b(19|20)\d{2}\b'),
        ('NUMBER',  r'\b\d+\b'),
        ('NEWLINE', r'\n'),
        ('SKIP',    r'[ \t]+'),   # whitespace — skip these
        ('WORD',    r'\b\w+\b'),  # catch-all
    
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

