"""
Diagnostic script: runs the traditional parser on cv_ajith only.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from lexer import Lexer
from parser import ResumeParser
from utils.file_extractor import extract_text_from_pdf

RESUMES = [
    r"D:\L\Resume-Parser\master\Resume-Parser\resumes\cv_ajith.pdf",
    r"D:\L\Resume-Parser\master\Resume-Parser\resumes\saurabhgupta.pdf",
    r"D:\L\Resume-Parser\master\Resume-Parser\resumes\mohammadmoghimicv.pdf",
    r"D:\L\Resume-Parser\master\Resume-Parser\resumes\resume.pdf",
    r"D:\L\Resume-Parser\master\Resume-Parser\resumes\comp_sci_resume.pdf",
]

def show_raw_text(path):
    text = extract_text_from_pdf(path)
    print("=== RAW TEXT (first 40 lines) ===")
    for i, line in enumerate(text.split("\n")[:40], 1):
        print(f"{i:3}: {repr(line)}")
    return text

for path in RESUMES:
    name = os.path.basename(path)
    print(f"\n{'='*70}")
    print(f"RESUME: {name}")
    print('='*70)

    text = show_raw_text(path)
    tokens = Lexer().tokenize(text)
    result = ResumeParser().build(tokens=tokens)

    print("\n--- PARSER OUTPUT ---")
    print(f"  name   : {result.name!r}")
    print(f"  email  : {result.email!r}")
    print(f"  phone  : {result.phone!r}")
    print(f"  education ({len(result.education)} entries):")
    for edu in result.education:
        print(f"    degree={edu.degree!r}  school={edu.school!r}  {edu.start_date}–{edu.end_date}")

