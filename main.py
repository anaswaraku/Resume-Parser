#fastapi app + endpoints
from fastapi import FastAPI, File, UploadFile, HTTPException
from utils.file_extractor import extract_text

from lexer import Lexer
from parser import Parser

import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

@app.get("/")
def home():
    return "hello"

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".rtf"}

@app.post("/parse-resume-hybrid")
async def parse_resume_hybrid(
    file: UploadFile = File(...),
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
    lexer = Lexer()
    text = extract_text(file.file, ext)
    tokens = lexer.tokenize(text)
    parser = Parser(tokens, text)
    ast = parser.parse()
    return ast.model_dump_json(indent=2)