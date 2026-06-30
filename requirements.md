# Hybrid Resume Parser API with LLM Assistance
## Requirement Specification Document

**Version:** 1.0  
**Date:** June 22, 2026  
**Project Type:** Educational Parser Learning Project  
**Technology Stack:** Python, FastAPI, OpenAI/Generic LLM

***

## 1. Executive Summary

### 1.1 Purpose
This document defines the requirements for building a **Hybrid Resume Parser API** that combines traditional parser techniques (lexer + parser + AST) with Large Language Model (LLM) assistance. The project serves as an educational tool to learn about parsers while demonstrating real-world application of hybrid parsing architectures.

### 1.2 Scope
- Build a FastAPI backend that accepts resume file uploads (PDF, DOCX, TXT, RTF)
- Extract structured data: name, email, phone, education, experience, skills
- Implement traditional lexical analysis and syntactic parsing
- Integrate LLM for complex pattern extraction
- Merge results from both parsers into a unified output

### 1.3 Target Audience
- Computer science students learning about parsers
- Developers interested in NLP and document parsing
- HR tech professionals building automation workflows

***

## 2. System Overview

### 2.1 Architecture Diagram

```
┌─────────────┐
│  Resume File │
│(PDF/DOCX/TXT)│
└──────┬──────┘
       │
       ▼
┌──────────────────┐
│  File Extractor   │  ← Extract text from binary formats
└──────┬───────────┘
       │
       ▼
┌─────────────────────────────────────────────────────┐
│              HYBRID PARSING ENGINE                   │
│  ┌─────────────────┐    ┌─────────────────┐         │
│  │ Traditional     │    │ LLM Parser      │         │
│  │ Parser          │    │ (OpenAI/Generic)│         │
│  │ ┌─────────────┐ │    │ ┌─────────────┐ │         │
│  │ │ Lexer       │ │    │ │ Prompt      │ │         │
│  │ │ (Tokenizer) │ │    │ │ Engineering │ │         │
│  │ └──────┬──────┘ │    │ └──────┬──────┘ │         │
│  │        ▼        │    │        ▼        │         │
│  │ ┌─────────────┐ │    │ ┌─────────────┐ │         │
│  │ │ Parser      │ │    │ │ JSON        │ │         │
│  │ │ (Grammar)   │ │    │ │ Response    │ │         │
│  │ └──────┬──────┘ │    │ └──────┬──────┘ │         │
│  │        ▼        │    │        ▼        │         │
│  │ ┌─────────────┐ │    │ ┌─────────────┐ │         │
│  │ │ AST         │ │    │ │ Pydantic    │ │         │
│  │ │ (ResumeAST) │ │    │ │ Validation  │ │         │
│  │ └─────────────┘ │    │ └─────────────┘ │         │
│  └────────┬────────┘    └────────┬────────┘         │
│           │                      │                   │
│           ▼                      ▼                   │
│  ┌─────────────────────────────────────────┐        │
│  │              Result Merging             │        │
│  │  (Traditional fills gaps, LLM adds      │        │
│  │   context-aware extraction)             │        │
│  └─────────────────┬───────────────────────┘        │
└────────────────────┼──────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────┐
│      Structured JSON Output     │
│  (Pydantic validated)           │
└─────────────────────────────────┘
```

### 2.2 Key Components

| Component | Responsibility | Parser Concept Learned |
|-----------|---------------|----------------------|
| **Lexer** | Tokenize raw text into EMAIL, PHONE, DATE, WORD tokens | Lexical Analysis  [youtube](https://www.youtube.com/watch?v=OMQUGRPFzh4) |
| **Parser** | Apply grammar rules to build hierarchical AST | Syntactic Analysis  [youtube](https://www.youtube.com/watch?v=OMQUGRPFzh4) |
| **AST** | Represent parsed data as nested objects | Abstract Syntax Tree  [youtube](https://www.youtube.com/watch?v=-BjWCx-50Lc) |
| **LLM Parser** | Extract complex/ambiguous sections using prompts | LLM-assisted parsing  [youtube](https://www.youtube.com/watch?v=NoPS2YruQ1Y) |
| **Merging Logic** | Combine results from both parsers | Hybrid architecture  [bankstatementparser](https://bankstatementparser.com) |

***

## 3. Functional Requirements

### 3.1 File Upload & Text Extraction

#### FR-01: Supported File Formats
**Priority:** High  
**Description:** System must accept resume files in the following formats:
- PDF (.pdf)
- DOCX (.docx)
- TXT (.txt)
- RTF (.rtf)

**Acceptance Criteria:**
- ✅ Upload endpoint accepts files up to 10MB
- ✅ System validates file extension before processing
- ✅ Returns error message for unsupported formats

#### FR-02: Text Extraction
**Priority:** High  
**Description:** System must extract plain text from binary file formats.

**Acceptance Criteria:**
- ✅ PDF extraction preserves paragraph structure
- ✅ DOCX extraction handles multi-line text
- ✅ TXT/RTF extraction returns raw text
- ✅ Handles encoding issues (UTF-8 fallback)

**Technical Implementation:**
```python
# utils/file_extractor.py
def extract_text_from_pdf(filepath: str) -> str
def extract_text_from_docx(filepath: str) -> str
def extract_text_from_txt(filepath: str) -> str
```

### 3.2 Traditional Parser

#### FR-03: Lexer (Tokenizer)
**Priority:** High  
**Description:** System must tokenize extracted text into meaningful tokens.

**Acceptance Criteria:**
- ✅ Detects EMAIL patterns using regex
- ✅ Detects PHONE patterns (10-digit formats)
- ✅ Detects DATE patterns (Month YYYY)
- ✅ Identifies WORD tokens for section headers
- ✅ Skips whitespace/newlines

**Token Types:**
| Token Type | Pattern Example |
|------------|---------------|
| `EMAIL` | john@example.com |
| `PHONE` | 123-456-7890 |
| `DATE` | Jan 2020, Mar 2024 |
| `WORD` | education, experience, skills |
| `NUMBER` | 2018, 2022 |
| `NEWLINE` | \n |

**Technical Implementation:**
```python
# lexer.py
class Lexer:
    TOKEN_PATTERNS = [
        ('EMAIL', r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
        ('PHONE', r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'),
        ('DATE', r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s*\d{4}\b'),
    ]
    
    def tokenize(self, text: str) -> List[Token]
```

#### FR-04: Parser (Grammar Rules)
**Priority:** High  
**Description:** System must apply grammar rules to build structured AST from tokens.

**Acceptance Criteria:**
- ✅ Identifies section headers (Education, Experience, Skills)
- ✅ Extracts email/phone from token stream
- ✅ Groups education entries (degree + school + dates)
- ✅ Groups experience entries (company + role + dates)
- ✅ Handles missing fields gracefully

**Technical Implementation:**
```python
# parser.py
class Parser:
    def __init__(self, tokens: List[Token])
    def parse(self) -> ResumeAST
    def parse_section(self, section: str)
```

#### FR-05: AST (Abstract Syntax Tree)
**Priority:** High  
**Description:** System must represent parsed data as hierarchical Pydantic objects.

**Acceptance Criteria:**
- ✅ Email/phone/schema validation via Pydantic
- ✅ Nested lists for education/experience
- ✅ Optional fields handle missing data
- ✅ JSON serialization supported

**Data Model:**
```python
# ast.py
class Education(BaseModel):
    degree: str
    school: str
    start_date: Optional[str]
    end_date: Optional[str]

class Experience(BaseModel):
    company: str
    role: str
    start_date: Optional[str]
    end_date: Optional[str]
    description: Optional[str]

class ResumeAST(BaseModel):
    name: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    education: List[Education] = []
    experience: List[Experience] = []
    skills: List[str] = []
```

### 3.3 LLM Parser

#### FR-06: LLM Integration
**Priority:** High  
**Description:** System must use LLM to extract complex/ambiguous resume sections.

**Acceptance Criteria:**
- ✅ Supports OpenAI GPT-4o-mini (default)
- ✅ Supports custom model selection
- ✅ Forces JSON response format
- ✅ Handles API errors gracefully
- ✅ Limits input to 10,000 characters (token budget)

**Technical Implementation:**
```python
# llm_parser.py
class LLMParser:
    def __init__(self, api_key: str, model: str = "gpt-4o-mini")
    def parse_with_llm(self, resume_text: str) -> ResumeData
    def _build_prompt(self, resume_text: str) -> str
```

#### FR-07: Prompt Engineering
**Priority:** High  
**Description:** System must use structured prompts to extract valid JSON.

**Acceptance Criteria:**
- ✅ Prompt includes JSON schema example
- ✅ Prompt specifies date format (YYYY-MM)
- ✅ Prompt handles missing data (null/empty arrays)
- ✅ Prompt enforced via system/user message roles

**Prompt Template:**
```text
You are an expert resume parser. Extract all information and return ONLY valid JSON.

Schema:
{
  "name": string,
  "email": string,
  "phone": string,
  "education": [{"degree": string, "school": string, "start_date": string, "end_date": string}],
  "experience": [{"company": string, "role": string, "start_date": string, "end_date": string}],
  "skills": [string]
}

Rules:
- Extract dates as "YYYY-MM" format
- If date is incomplete, use null
- Return empty arrays if no data found
```

#### FR-08: JSON Validation
**Priority:** High  
**Description:** System must validate LLM output against Pydantic schema.

**Acceptance Criteria:**
- ✅ Parses LLM JSON response
- ✅ Validates with Pydantic model
- ✅ Returns empty ResumeData on validation failure
- ✅ Logs validation errors for debugging

**Technical Implementation:**
```python
try:
    data = json.loads(llm_output)
    return ResumeData(**data)  # Pydantic validation
except Exception as e:
    print(f"LLM JSON parsing error: {e}")
    return ResumeData()  # Fallback
```

### 3.4 Result Merging

#### FR-09: Hybrid Merging Logic
**Priority:** High  
**Description:** System must merge results from traditional and LLM parsers.

**Acceptance Criteria:**
- ✅ Traditional parser results used as baseline
- ✅ LLM fills gaps where traditional parser failed
- ✅ Priority: LLM overrides traditional for name/email/phone
- ✅ Education/experience merged by appending lists
- ✅ Skills deduplicated in final output

**Merging Algorithm:**
```python
merged = traditional_result
if not merged.name and llm_result.name:
    merged.name = llm_result.name
if not merged.email and llm_result.email:
    merged.email = llm_result.email
if not merged.phone and llm_result.phone:
    merged.phone = llm_result.phone
if not merged.education and llm_result.education:
    merged.education = llm_result.education
if not merged.experience and llm_result.experience:
    merged.experience = llm_result.experience
if not merged.skills and llm_result.skills:
    merged.skills = llm_result.skills
```

#### FR-10: Output Format
**Priority:** High  
**Description:** API must return structured JSON with parsing metadata.

**Acceptance Criteria:**
- ✅ Returns merged result as primary output
- ✅ Includes traditional_parser output (for comparison)
- ✅ Includes llm_parser output (for comparison)
- ✅ Includes parsing_method flag ("hybrid" or "traditional_only")

**Response Schema:**
```json
{
  "traditional_parser": {
    "name": null,
    "email": "john@example.com",
    "phone": null,
    "education": [],
    "experience": [],
    "skills": []
  },
  "llm_parser": {
    "name": "John Doe",
    "email": "john@example.com",
    "phone": "123-456-7890",
    "education": [...],
    "experience": [...],
    "skills": ["Python", "FastAPI"]
  },
  "merged_result": {
    "name": "John Doe",
    "email": "john@example.com",
    "phone": "123-456-7890",
    "education": [...],
    "experience": [...],
    "skills": ["Python", "FastAPI"]
  },
  "parsing_method": "hybrid"
}
```

### 3.5 API Endpoints

#### FR-11: Parse Resume Endpoint
**Priority:** High  
**Description:** Main endpoint for resume parsing.

**Acceptance Criteria:**
- ✅ Endpoint: `POST /parse-resume-hybrid`
- ✅ Accepts file upload via `multipart/form-data`
- ✅ Optional query parameter: `use_llm=true/false`
- ✅ Returns 200 OK on success
- ✅ Returns 400 Bad Request for invalid files
- ✅ Returns 500 Internal Server Error on parser failures

**API Specification:**
```python
@app.post("/parse-resume-hybrid")
async def parse_resume_hybrid(
    file: UploadFile = File(...),
    use_llm: bool = Query(default=True)
):
    # ... parsing logic
    return merged_result
```

#### FR-12: Error Handling
**Priority:** High  
**Description:** API must handle errors gracefully with clear messages.

**Acceptance Criteria:**
- ✅ File too large → 400 with message "File size exceeds 10MB limit"
- ✅ Unsupported format → 400 with message "Unsupported file format: {ext}"
- ✅ LLM API error → 500 with message "LLM parsing failed: {error}"
- ✅ Text extraction error → 500 with message "Failed to extract text from file"

***

## 4. Non-Functional Requirements

### 4.1 Performance

#### NFR-01: Response Time
**Priority:** Medium  
**Requirement:**
- Traditional parser only: < 500ms per resume
- Hybrid parser (with LLM): < 5 seconds per resume
- File upload + extraction: < 1 second for files up to 10MB

### 4.2 Reliability

#### NFR-02: Availability
**Priority:** Medium  
**Requirement:**
- API must handle concurrent requests (up to 10 at once)
- Graceful degradation if LLM service is unavailable (fallback to traditional parser)

#### NFR-03: Accuracy
**Priority:** High  
**Requirement:**
- Traditional parser accuracy (email/phone): ≥ 95%
- LLM parser accuracy (complex sections): ≥ 85%
- Hybrid accuracy (merged): ≥ 90%

### 4.3 Security

#### NFR-04: API Key Protection
**Priority:** High  
**Requirement:**
- OpenAI API key stored in environment variable (not code)
- No API keys logged or exposed in error messages

#### NFR-05: File Validation
**Priority:** Medium  
**Requirement:**
- Validate file extension before processing
- Reject executable files (.exe, .bat, .sh)

### 4.4 Scalability

#### NFR-06: Token Budget Management
**Priority:** Medium  
**Requirement:**
- Limit resume text to 10,000 characters for LLM
- Implement chunked parsing for longer resumes (future enhancement)

### 4.5 Maintainability

#### NFR-07: Code Organization
**Priority:** Medium  
**Requirement:**
- Modular structure (lexer.py, parser.py, llm_parser.py, main.py)
- Type hints on all functions
- Docstrings for public methods

#### NFR-08: Logging
**Priority:** Low  
**Requirement:**
- Log parsing errors with timestamps
- Log LLM API calls (without sensitive data)

***

## 5. Technical Requirements

### 5.1 Technology Stack

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| **Backend Framework** | FastAPI | 0.100+ | Async API with auto-docs |
| **Language** | Python | 3.9+ | Parser implementation |
| **Validation** | Pydantic | 2.0+ | Schema validation |
| **LLM Provider** | OpenAI | 1.0+ | GPT-4o-mini integration |
| **PDF Parsing** | pdfplumber | 0.10+ | PDF text extraction |
| **DOCX Parsing** | python-docx | 0.8+ | DOCX text extraction |
| **Async Server** | uvicorn | 0.23+ | ASGI server |
| **File Uploads** | python-multipart | 0.0+ | Multipart form handling |

### 5.2 Project Structure

```
hybrid_resume_parser/
├── main.py                  # FastAPI app + endpoints
├── lexer.py                 # Tokenizer implementation
├── parser.py                # Grammar-based parser
├── ast.py                   # Pydantic data models
├── llm_parser.py            # LLM integration
├── prompts/
│   └── resume_extraction.txt # LLM prompt template
├── utils/
│   └── file_extractor.py    # PDF/DOCX extraction
├── tests/
│   ├── test_resumes/        # Sample resume files
│   ├── test_lexer.py
│   ├── test_parser.py
│   └── test_llm_parser.py
├── .env                     # Environment variables (API keys)
├── requirements.txt         # Python dependencies
└── README.md                # Project documentation
```

### 5.3 Dependencies

```txt
# requirements.txt
fastapi>=0.100.0
uvicorn>=0.23.0
python-multipart>=0.0.6
pydantic>=2.0.0
openai>=1.0.0
pdfplumber>=0.10.0
python-docx>=0.8.0
```

### 5.4 Environment Configuration

```bash
# .env
OPENAI_API_KEY=your_openai_api_key_here
LLM_MODEL=gpt-4o-mini
MAX_FILE_SIZE=10485760  # 10MB in bytes
MAX_TEXT_LENGTH=10000   # 10K characters for LLM
```

***

## 6. Educational Objectives

### 6.1 Parser Concepts to Learn

| Concept | How This Project Demonstrates It |
|---------|--------------------------------|
| **Lexical Analysis** | Lexer tokenizes text into EMAIL, PHONE, DATE tokens  [youtube](https://www.youtube.com/watch?v=OMQUGRPFzh4) |
| **Syntactic Analysis** | Parser applies grammar rules to build structure  [youtube](https://www.youtube.com/watch?v=OMQUGRPFzh4) |
| **Abstract Syntax Tree** | ResumeAST represents hierarchical parsed data  [youtube](https://www.youtube.com/watch?v=-BjWCx-50Lc) |
| **Top-Down Parsing** | Parser starts from section headers and expands downward  [youtube](https://www.youtube.com/watch?v=OMQUGRPFzh4) |
| **Grammar Rules** | TOKEN_PATTERNS define valid token patterns  [youtube](https://www.youtube.com/watch?v=OMQUGRPFzh4) |
| **Error Detection** | Parser reports missing/invalid fields  [geeksforgeeks](https://www.geeksforgeeks.org/compiler-design/introduction-of-parsing-ambiguity-and-parsers-set-1/) |

### 6.2 LLM Concepts to Learn

| Concept | How This Project Demonstrates It |
|---------|--------------------------------|
| **Prompt Engineering** | Structured prompts force JSON output  [youtube](https://www.youtube.com/watch?v=NoPS2YruQ1Y) |
| **Context-Aware Extraction** | LLM understands resume context for ambiguous sections  [medium](https://medium.com/@bravekjh/building-an-ai-agent-for-parsing-a-practical-guide-with-python-code-1aeb2b66e3e5) |
| **JSON Schema Enforcement** | Pydantic validates LLM output  [medium](https://medium.com/@bravekjh/building-an-ai-agent-for-parsing-a-practical-guide-with-python-code-1aeb2b66e3e5) |
| **Token Budget Management** | Character limits stay within token constraints  [youtube](https://www.youtube.com/watch?v=37i6Gx1uvVs) |
| **Error Handling** | Fallback logic when LLM returns invalid JSON  [medium](https://medium.com/@bravekjh/building-an-ai-agent-for-parsing-a-practical-guide-with-python-code-1aeb2b66e3e5) |

### 6.3 Architecture Concepts to Learn

| Concept | How This Project Demonstrates It |
|---------|--------------------------------|
| **Hybrid Architecture** | Combines deterministic + probabilistic parsing  [bankstatementparser](https://bankstatementparser.com) |
| **Service Orchestration** | FastAPI coordinates multiple parsing services  [medium](https://medium.com/@bravekjh/building-an-ai-agent-for-parsing-a-practical-guide-with-python-code-1aeb2b66e3e5) |
| **Result Merging** | Algorithms merge outputs from multiple sources  [bankstatementparser](https://bankstatementparser.com) |
| **Graceful Degradation** | System works without LLM (traditional fallback)  [medium](https://medium.com/@bravekjh/building-an-ai-agent-for-parsing-a-practical-guide-with-python-code-1aeb2b66e3e5) |

***

## 7. Acceptance Criteria

### 7.1 Minimum Viable Product (MVP)

**Must have for MVP:**
- ✅ File upload endpoint accepts PDF/DOCX/TXT
- ✅ Traditional parser extracts email/phone
- ✅ LLM parser extracts name/education/experience
- ✅ Merged result returned as JSON
- ✅ API documentation (Swagger UI) available

### 7.2 Enhanced Features (Post-MVP)

**Optional enhancements:**
- ⬜ Confidence scoring (how much LLM improved extraction)
- ⬜ Chunked parsing for resumes > 10K characters
- ⬜ Local LLM support (Ollama/LLaMA)
- ⬜ Job description matching endpoint
- ⬜ Batch processing (multiple files)
- ⬜ Unit tests with 80%+ coverage
- ⬜ Docker containerization

***

## 8. Testing Requirements

### 8.1 Test Cases

#### TC-01: Email Extraction (Traditional Parser)
**Input:** Resume text containing "john@example.com"  
**Expected:** `merged_result.email = "john@example.com"`  
**Parser:** Traditional only

#### TC-02: Name Extraction (LLM Parser)
**Input:** Resume starting with "John Doe - Software Engineer"  
**Expected:** `merged_result.name = "John Doe"`  
**Parser:** LLM only

#### TC-03: Education Extraction (LLM Parser)
**Input:** Section "Education: BSc Computer Science, XYZ University, 2018-2022"  
**Expected:** `merged_result.education = [{"degree": "BSc...", "school": "XYZ...", ...}]`  
**Parser:** LLM only

#### TC-04: Hybrid Merging
**Input:** Traditional extracts email, LLM extracts name  
**Expected:** `merged_result.name` and `merged_result.email` both populated  
**Parser:** Hybrid

#### TC-05: Unsupported File Format
**Input:** Upload .exe file  
**Expected:** 400 Bad Request with error message  
**Parser:** N/A (pre-validation)

### 8.2 Test Data

**Required sample resumes:**
- 5 PDF resumes (various layouts)
- 5 DOCX resumes (various layouts)
- 2 resumes with missing fields (edge cases)
- 1 resume > 10K characters (long format)

***

## 9. Deployment Requirements

### 9.1 Development Environment

**Requirements:**
- Python 3.9+ installed
- Virtual environment activated (`python -m venv venv`)
- Dependencies installed (`pip install -r requirements.txt`)

### 9.2 Running the Application

```bash
# Start FastAPI server
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Access API
# - Swagger UI: http://localhost:8000/docs
# - Health check: http://localhost:8000/
```

### 9.3 API Usage Example

```bash
# Parse resume with hybrid (default)
curl -X POST "http://localhost:8000/parse-resume-hybrid" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@resume.pdf"

# Parse resume with traditional parser only
curl -X POST "http://localhost:8000/parse-resume-hybrid" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@resume.pdf" \
  -F "use_llm=false"
```

***

## 10. References

### 10.1 Learning Resources

| Resource | Type | Link |
|----------|------|------|
| "What is a Parser? A Beginner's Guide" | Video |  [youtube](https://www.youtube.com/watch?v=OMQUGRPFzh4) |
| "Introduction to Parsers" (GeeksforGeeks) | Article |  [geeksforgeeks](https://www.geeksforgeeks.org/compiler-design/introduction-of-parsing-ambiguity-and-parsers-set-1/) |
| "Introduction To Parsers" | Video |  [youtube](https://www.youtube.com/watch?v=-BjWCx-50Lc) |
| "Writing your own programming language with Python" | Article |  [medium](https://medium.com/@marcelogdeandrade/writing-your-own-programming-language-and-compiler-with-python-a468970ae6df) |
| "Build a Resume Parser API with FastAPI" | Video |  [youtube](https://www.youtube.com/watch?v=c2ifRxzqmi0) |
| "Build your own Resume Parser Using Python and Gen AI" | Video |  [youtube](https://www.youtube.com/watch?v=NoPS2YruQ1Y) |
| "Building an AI Agent for Parsing" | Article |  [medium](https://medium.com/@bravekjh/building-an-ai-agent-for-parsing-a-practical-guide-with-python-code-1aeb2b66e3e5) |
| "PDF to JSON: LLM-Powered Data Extraction" | Video |  [youtube](https://www.youtube.com/watch?v=37i6Gx1uvVs) |

### 10.2 GitHub Projects

| Project | Purpose | Link |
|---------|---------|------|
| `Resume-Parser-OpenAI` | Complete code walkthrough |  [youtube](https://www.youtube.com/watch?v=NoPS2YruQ1Y) |
| `ResumeParser-LLM` | OpenRouter + DeepSeek integration |  [github](https://github.com/Bernardbyy/ResumeParser-LLM) |
| `llm-parse` | General LLM parsing library |  [github](https://github.com/tanchangsheng/llm-parse) |

***

### 11.1 Glossary

| Term | Definition |
|------|------------|
| **Lexer** | Tokenizer that converts raw text into tokens |
| **Parser** | Component that applies grammar rules to build structure |
| **AST** | Abstract Syntax Tree representing hierarchical data |
| **LLM** | Large Language Model (e.g., GPT-4, LLaMA) |
| **Hybrid Parser** | System combining traditional + LLM parsing |
| **Pydantic** | Python data validation library using type hints |


 
