from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from utils.file_extractor import extract_text_from_pdf, extract_text_from_docx, extract_text_from_txt
from llm_parser import LLMParser
from lexer import Lexer
from parser import Parser

import os
import tempfile
from dotenv import load_dotenv

load_dotenv()

llm_parser = LLMParser(
    api_key=os.getenv("GROQ_API_KEY"),
    model=os.getenv("LLM_MODEL", "llama3-8b-8192")
)

app = FastAPI()

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".rtf"}
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 10_000_000))


@app.get("/")
def home():
    return {"status": "ok"}


@app.post("/parse-resume-hybrid")
async def parse_resume_hybrid(
    file: UploadFile = File(...),
    use_llm: bool = Query(default=True)
):
    # Validate extension
    ext = os.path.splitext(file.filename or "")[-1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file format: {ext}")

    # Validate size
    if file.size is not None and file.size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File size exceeds 10MB limit")

    # Read file bytes and write to temp file (extractors need a filepath)
    await file.seek(0)
    contents = await file.read()

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(contents)
            tmp_path = tmp.name

        # Extract plain text based on file type
        if ext == ".pdf":
            text = extract_text_from_pdf(tmp_path)
        elif ext == ".docx":
            text = extract_text_from_docx(tmp_path)
        else:  # .txt or .rtf
            text = extract_text_from_txt(tmp_path)

    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract text: {e}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    if not text.strip():
        raise HTTPException(status_code=400, detail="File appears to be empty or unreadable.")

    # Route to LLM or traditional parser
    if use_llm:
        try:
            return llm_parser.parse_with_llm(text)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"LLM parsing failed: {e}")
    else:
        tokens = Lexer().tokenize(text)
        ast = Parser(tokens).parse()
        return ast