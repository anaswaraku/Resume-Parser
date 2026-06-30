# Hybrid Resume Parser API with LLM Assistance

A FastAPI-based Resume Parser that combines **traditional compiler parsing techniques (Lexer → Parser → AST)** with **Large Language Models (LLMs)** to accurately extract structured information from resumes.

This project demonstrates how deterministic parsing and AI-powered extraction can work together to build an intelligent document parser.

---

## Overview

The Hybrid Resume Parser accepts resume files in multiple formats and extracts structured information such as:

- Name
- Email
- Phone Number
- Education
- Work Experience
- Skills

The parser uses two approaches:

- **Traditional Parser**
  - Lexer (Tokenization)
  - Grammar-based Parser
  - Abstract Syntax Tree (AST)

- **LLM Parser**
  - GPT-4o-mini (or compatible LLM)
  - Prompt Engineering
  - JSON Validation using Pydantic

Finally, both outputs are merged into a single high-quality response.

---

# Architecture

```
Resume File
      │
      ▼
Text Extraction
      │
      ▼
 ┌──────────────────────────┐
 │      Hybrid Parser       │
 │                          │
 │ Traditional Parser       │
 │   • Lexer                │
 │   • Parser               │
 │   • AST                  │
 │                          │
 │ LLM Parser               │
 │   • Prompt               │
 │   • JSON Output          │
 │   • Validation           │
 └──────────┬───────────────┘
            │
            ▼
     Result Merging
            │
            ▼
     Structured JSON
```

---

#  Features

- Upload Resume (PDF, DOCX, TXT, RTF)
- Text Extraction
- Traditional Resume Parsing
- LLM-based Resume Parsing
- Hybrid Result Merging
- FastAPI REST API
- Automatic Swagger Documentation
- Pydantic Validation
- Error Handling
- Environment Variable Configuration

---

# 🛠 Tech Stack

| Technology | Purpose |
|------------|---------|
| Python 3.9+ | Programming Language |
| FastAPI | REST API |
| Pydantic | Data Validation |
| GROQ API | LLM Extraction |
| pdfplumber | PDF Parsing |
| python-docx | DOCX Parsing |
| Uvicorn | ASGI Server |

---


---

# Installation

Clone the repository

```bash
git clone https://github.com/anaswaraku/Resume-Parser.git
```

Navigate into the project

```bash
cd hybrid-resume-parser
```

Create a virtual environment

```bash
python -m venv venv
```

Activate it

### Windows

```bash
venv\Scripts\activate
```

### Linux / macOS

```bash
source venv/bin/activate
```

Install dependencies

```bash
pip install -r requirements.txt
```

---

# Environment Variables

Create a `.env` file

```env
GROQ_API_KEY=your_api_key
LLM_MODEL=gpt-4o-mini
MAX_FILE_SIZE=10485760
MAX_TEXT_LENGTH=10000
```

---

# ▶ Running the Application

```bash
uvicorn main:app --reload
```

Application

```
http://localhost:8000
```

Swagger UI

```
http://localhost:8000/docs
```

ReDoc

```
http://localhost:8000/redoc
```

---

# 📤 API Endpoint

## 1. Parse Resume (Hybrid)

**POST** `/parse-resume-hybrid`

Parses a resume using both a **Traditional Parser** and an **LLM Parser**, then merges the results.

### Features

- Supports PDF, DOCX, TXT, and RTF resumes
- Traditional parsing (Lexer + Parser + AST)
- LLM-powered extraction
- Hybrid result merging
- Confidence score generation

### Query Parameters

| Parameter | Type | Default | Description |
|----------|------|---------|-------------|
| use_llm | boolean | true | Enable or disable the LLM parser |

### Request

```
multipart/form-data
```

| Field | Type |
|-------|------|
| file | Resume File |

### Response

Returns

- Traditional parser output
- LLM parser output
- Merged result
- Confidence metrics
- Parsing method

---

## 2. Batch Resume Parsing

**POST** `/parse-resume-batch`

Parse multiple resumes in a single request.

### Features

- Multiple file upload
- Hybrid parsing
- Batch processing
- Individual parsing results

---

## 3. Job Matching

**POST** `/match-job`

Matches a parsed resume against a job description.

### Request

- Resume
- Job Description

### Returns

- Match Score
- Matching Skills
- Missing Skills
- Candidate Strengths
- Improvement Suggestions

---

## 4. Batch Job Matching

**POST** `/match-job-batch`

Matches multiple resumes against a single job description.

### Returns

- Match score for each resume
- Ranked candidates
- Individual recommendations

---

#  Traditional Parser

The traditional parser demonstrates compiler concepts:

- Lexical Analysis
- Tokenization
- Grammar Rules
- Parsing
- Abstract Syntax Tree (AST)

Supported Tokens

- EMAIL
- PHONE
- DATE
- WORD
- NUMBER

---

# LLM Parser

The AI parser uses GPT models to extract:

- Name
- Education
- Experience
- Skills

It returns structured JSON validated using Pydantic.

---

# Hybrid Parsing Strategy

1. Extract text from the resume.
2. Run the Traditional Parser.
3. Run the LLM Parser.
4. Merge both results.
5. Return the final structured JSON.

This improves extraction accuracy while maintaining deterministic parsing for simpler fields.

---

# Learning Objectives

This project demonstrates:

- Compiler Design
- Lexical Analysis
- Parsing Techniques
- Abstract Syntax Trees
- Prompt Engineering
- FastAPI Development
- Pydantic Validation
- Hybrid AI Architectures
- REST API Development

---

# Author

**Anaswara K U**

GitHub: https://github.com/anaswaraku

## ⭐ If you found this project useful, consider giving it a star!
