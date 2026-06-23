import pdfplumber
from docx import Document
from striprtf.striprtf import rtf_to_text

import re 

def decode_bytes(bytes_content) -> str:
    """
    Safely decode bytes content.
    Try UTF-8, then CP1252/Windows-1252, and finally fallback to UTF-8 with errors replaced.
    """
    try:
        return bytes_content.decode("utf-8")
    except UnicodeDecodeError:
        pass
    try:
        return bytes_content.decode("cp1252")
    except UnicodeDecodeError:
        pass
    return bytes_content.decode("utf-8", errors="replace")

def clean_text(text):
    # Normalize line endings
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    # Collapse 3 or more consecutive newlines to exactly 2 newlines (preserves paragraph separation)
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Collapse multiple spaces/tabs to a single space
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()

def extract_text(file_obj, ext: str):
    """
    Extract text from an uploaded file without saving to disk.
    file_obj: file-like object
    filename: original filename (to detect extension)
    """
    text = ""
    if ext == ".pdf":
        with pdfplumber.open(file_obj) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    elif ext == ".docx":
        doc = Document(file_obj)
        parts = []
        # Extract paragraph text
        for para in doc.paragraphs:
            if para.text.strip():
                parts.append(para.text)
        # Extract table text
        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                if row_text:
                    parts.append(row_text)
        text = "\n\n".join(parts)
    elif ext == ".txt":
        file_obj.seek(0)
        text = decode_bytes(file_obj.read())
    elif ext == ".rtf":
        file_obj.seek(0)
        rtf_content = decode_bytes(file_obj.read())
        # Convert RTF formatting to plain text
        text = rtf_to_text(rtf_content)
        # Combine surrogate pairs into single characters to preserve emojis and avoid encoding crashes
        try:
            text = text.encode("utf-16", "surrogatepass").decode("utf-16")
        except Exception:
            pass
    else:
        return "Unsupported FIle"
    return clean_text(text)

def extract_text_from_pdf(filepath: str) -> str:
    """Extract text from a PDF file path."""
    with open(filepath, "rb") as f:
        return extract_text(f, ".pdf")

def extract_text_from_docx(filepath: str) -> str:
    """Extract text from a DOCX file path."""
    with open(filepath, "rb") as f:
        return extract_text(f, ".docx")

def extract_text_from_txt(filepath: str) -> str:
    """Extract text from a TXT file path."""
    with open(filepath, "rb") as f:
        return extract_text(f, ".txt")

def extract_text_from_rtf(filepath: str) -> str:
    """Extract text from an RTF file path."""
    with open(filepath, "rb") as f:
        return extract_text(f, ".rtf")