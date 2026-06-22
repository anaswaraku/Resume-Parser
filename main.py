#fastapi app + endpoints
from fastapi import FastAPI, File, UploadFile
from utils.file_extractor import extract_text

from lexer import Lexer
from parser import Parser
from utils import file_extractor

app = FastAPI()

@app.get("/")
def home():
    return "hello"

@app.post("/parse-resume-hybrid")
async def parse_resume_hybrid(
    file: UploadFile  = File(...),
    # #use_llm: bool = Query(default=True)
):
    await file.seek(0)  # ensure we're at the start of the file
    lexer= Lexer()
    text = extract_text(file.file,file.filename)# pass the raw file-like object
    tokens = lexer.tokenize(text)
    parser = Parser(tokens,text)
    ast = parser.parse()
    return (ast.model_dump_json(indent=2))