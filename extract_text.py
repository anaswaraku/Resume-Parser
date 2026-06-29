
import sys
from utils.file_extractor import extract_text_from_pdf

if __name__ == "__main__":
    if len(sys.argv) > 1:
        text = extract_text_from_pdf(sys.argv[1])
        print(text)
    else:
        print("Please provide a PDF file path.")
