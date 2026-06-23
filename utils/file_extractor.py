import pdfplumber
from docx import Document
from striprtf.striprtf import rtf_to_text

import re 

def clean_text(text):
    text = re.sub(r'\n+','\n', text)
    text = re.sub(r' +',' ', text)
    return text.strip()

def extract_text(file_obj, ext: str):
    """
    Extract text from an uploaded file without saving to disk.
    file_obj: file-like object
    filename: original filename (to detect extension)
    """
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
    elif ext == ".txt":
        file_obj.seek(0)
        text = file_obj.read().decode("utf-8")
    elif ext==".rtf":
        file_obj.seek(0)
        rtf_content = file_obj.read().decode("utf-8",errors="ignore")
        text = rtf_to_text(rtf_content).encode("utf-8", "ignore").decode("utf-8")
            
    else:
        return "Unsupported FIle"
    return clean_text(text)