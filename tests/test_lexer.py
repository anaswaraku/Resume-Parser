import pytest
from lexer import Lexer, Token
 
def test_lexer_words_and_separators():
    lexer = Lexer()
    # 'C++' — WORD pattern is [A-Za-z0-9_.'\-]+ so '+' is a SEPARATOR
    text = "Python, JavaScript, Node.js"
    tokens = lexer.tokenize(text)

    types  = [t.type  for t in tokens]
    values = [t.value for t in tokens]
    assert "WORD"      in types
    assert "SEPARATOR" in types
    assert "Python"       in values
    assert "JavaScript"   in values
    assert "Node.js"      in values
 
def test_lexer_emails():
    lexer = Lexer()
    emails = ["john.doe@example.com", "jane-doe@sub.domain.org", "test_user+name@gmail.com"]
    for email in emails:
        tokens = lexer.tokenize(email)
        assert len(tokens) == 1
        assert tokens[0].type == "EMAIL"
        assert tokens[0].value == email
 
def test_lexer_phones():
    lexer = Lexer()
    phones = ["+91 9876543210"]
    for phone in phones:
        tokens = lexer.tokenize(phone)
        assert len(tokens) == 1
        assert tokens[0].type == "PHONE"
        assert tokens[0].value == phone
 
def test_lexer_urls():
    lexer = Lexer()
    urls = [
        "http://google.com",
        "https://linkedin.com/in/username",
        "www.github.com/project",
        "github.com/another-project"
    ]
    for url in urls:
        tokens = lexer.tokenize(url)
        assert len(tokens) == 1
        assert tokens[0].type == "URL"
        assert tokens[0].value == url
 
def test_lexer_dates():
    lexer = Lexer()
    # Lexer recognises month-name + year as DATE
    for text in ["Jan 2020", "January 2020"]:
        tokens = lexer.tokenize(text)
        assert len(tokens) == 1, f"Expected 1 token for {text!r}, got {tokens}"
        assert tokens[0].type == "DATE"
        assert tokens[0].value == text

    # "01/2020" is NOT a DATE — lexer has no MM/YYYY rule; it becomes WORD+SEPARATOR+YEAR
    tokens = lexer.tokenize("01/2020")
    types = [t.type for t in tokens]
    assert "DATE" not in types
 
def test_lexer_numbers():
    lexer = Lexer()
    # 4-digit years (19xx / 20xx) are tagged YEAR, not NUMBER
    tokens = lexer.tokenize("2026")
    assert len(tokens) == 1
    assert tokens[0].type == "YEAR"
    assert tokens[0].value == "2026"

    # Plain numbers that aren't years come through as WORD (catch-all)
    tokens = lexer.tokenize("123")
    assert len(tokens) == 1
    assert tokens[0].value == "123"
 
def test_lexer_newlines():
    lexer = Lexer()
    text = "Hello\nWorld"
    tokens = lexer.tokenize(text)
    assert len(tokens) == 3
    assert tokens[0].type == "WORD"
    assert tokens[1].type == "NEWLINE"
    assert tokens[2].type == "WORD"
 
def test_lexer_unknown_characters():
    lexer = Lexer()
    text = "Hello @#$% World"
    tokens = lexer.tokenize(text)
    assert len(tokens) == 2
    assert tokens[0] == Token("WORD", "Hello", 0)
    assert tokens[1] == Token("WORD", "World", 11)
 
def test_lexer_positions():
    lexer = Lexer()
    text = "Word1\tWord2"
    tokens = lexer.tokenize(text)
    assert len(tokens) == 2
    assert tokens[0].position == 0
    assert tokens[1].position == 6
 
def test_lexer_complex_resume_snippet():
    lexer = Lexer()
    text = "Name: John Doe\nEmail: john@example.com\nPhone: (123) 456-7890\nSkills: Python, C++"
    tokens = lexer.tokenize(text)
    
    # Let's check some key tokens in the stream
    types = [t.type for t in tokens]
    
    assert "EMAIL" in types
    assert "PHONE" in types
    assert "SEPARATOR" in types
    
    # Locate exact values
    email_tok = next(t for t in tokens if t.type == "EMAIL")
    assert email_tok.value == "john@example.com"
    
    phone_tok = next(t for t in tokens if t.type == "PHONE")
    assert phone_tok.value == "(123) 456-7890"