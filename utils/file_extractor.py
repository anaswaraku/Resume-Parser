import re


def extract_text_from_pdf(filepath: str) -> str:
    """PDF → plain text, page structure preserved. Tries pdfplumber, falls back to PyPDF2."""
    try:
        import pdfplumber
        pages = []
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t: pages.append(t.strip())
        return "\n\n".join(pages)
    except ImportError:
        pass
    except Exception as e:
        raise RuntimeError(f"pdfplumber error: {e}")

    try:
        from PyPDF2 import PdfReader
        pages = []
        for page in PdfReader(filepath).pages:
            t = page.extract_text()
            if t: pages.append(t.strip())
        return "\n\n".join(pages)
    except ImportError:
        raise RuntimeError("Install pdfplumber: pip install pdfplumber")
    except Exception as e:
        raise RuntimeError(f"PDF read error: {e}")


def extract_text_from_docx(filepath: str) -> str:
    """DOCX → plain text. Reads paragraphs AND table cells (many resumes use tables)."""
    try:
        from docx import Document
    except ImportError:
        raise RuntimeError("Install python-docx: pip install python-docx")
    try:
        doc = Document(filepath)
        lines = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        for table in doc.tables:
            for row in table.rows:
                cells = [c.text.strip() for c in row.cells if c.text.strip()]
                if cells: lines.append("  ".join(cells))
        return "\n".join(lines)
    except Exception as e:
        raise RuntimeError(f"DOCX read error: {e}")


def extract_text_from_txt(filepath: str) -> str:
    """TXT/RTF → plain text. Encoding order: utf-8-sig → utf-8 → latin-1."""
    content = ""
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            with open(filepath, "r", encoding=enc) as f:
                content = f.read()
            break
        except UnicodeDecodeError:
            continue
        except Exception as e:
            raise RuntimeError(f"File read error: {e}")

    if not content:
        raise RuntimeError("Could not decode file with any supported encoding.")

    if filepath.lower().endswith(".rtf"):
        content = _strip_rtf(content)

    return content


def _strip_rtf(text: str) -> str:
    """Remove RTF control sequences, preserve paragraph breaks."""
    text = re.sub(r'\\par\b|\\line\b', '\n', text, flags=re.I)
    text = re.sub(r'\\u(-?\d+)\?', lambda m: chr(int(m.group(1)) % 65536), text)
    prev = None
    while prev != text:                          # iteratively remove nested braces
        prev = text
        text = re.sub(r'\{[^{}]*\}', ' ', text)
    text = re.sub(r'\\[a-z]+\-?\d*\s?', ' ', text)
    text = re.sub(r'[{}\\]', ' ', text)
    lines = [re.sub(r'[ \t]+', ' ', ln).strip() for ln in text.split('\n')]
    return '\n'.join(ln for ln in lines if ln)