

from utils.file_extractor import extract_text_from_txt
txt = extract_text_from_txt("resumes/resume.txt")
from lexer import Lexer
t = Lexer()
token = t.tokenize(txt)

from parser import LineBuilder,HeaderBuilder,ResumeParser
l = LineBuilder()
l=l.build(tokens=token)
section = HeaderBuilder()
s=section.build(lines=l)
print(ResumeParser().build(tokens=token))