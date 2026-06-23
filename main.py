#fastapi app + endpoints
from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from utils.file_extractor import extract_text
from llm_parser import LLMParser
from lexer import Lexer
from parser import Parser

import os
from dotenv import load_dotenv

load_dotenv()

llm_parser = LLMParser(api_key=os.getenv("GROQ_API_KEY"), model=os.getenv("LLM_MODEL"))

app = FastAPI()

@app.get("/")
def home():
    return "hello"

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".rtf"}

@app.post("/parse-resume-hybrid")
async def parse_resume_hybrid(
    file: UploadFile = File(...),
    use_llm: bool = Query(default=True)
):
    # Validate by file extension
    ext = os.path.splitext(file.filename)[-1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format: {ext}"
        )

    max_size = int(os.getenv("MAX_FILE_SIZE", 10_000_000))
    if file.size is not None and file.size > max_size:
        raise HTTPException(
            status_code=400,
            detail="File size exceeds 10MB limit"
        )

    await file.seek(0)
    text = extract_text(file.file, ext)
    if use_llm:
        return(llm_parser.parse_with_llm(text))
    else:
        lexer = Lexer()
        tokens = lexer.tokenize(text)
        parser = Parser(tokens, text)
        ast = parser.parse()
        return ast