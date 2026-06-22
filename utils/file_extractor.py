import os
import pdfplumber
from docx import Document

def extract_text(file_obj, filename: str):
    """
    Extract text from an uploaded file without saving to disk.
    file_obj: file-like object
    filename: original filename (to detect extension)
    """
    ext = os.path.splitext(filename)[1].lower()
    text = ""
    if ext==".pdf":
        with pdfplumber.open(file_obj) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    elif ext==".docx":
        doc = Document(file_obj)
        for para in doc.paragraphs:
            if para.text.strip():
                text+= para.text
    return text
