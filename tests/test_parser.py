from lexer import Lexer
from parser import Parser
from utils import file_extractor

txt = file_extractor.extract_text("resumes/resume.pdf",".pdf")
lexer= Lexer()
tokens = lexer.tokenize(txt)

parser=Parser(tokens,txt)
ast = parser.parse()

print(ast.model_dump_json(indent=2))