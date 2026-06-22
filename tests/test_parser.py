from lexer import Lexer
from parser import Parser

txt = """RESUME

Name: Ananya Sharma  
Email: ananya.sharma@email.com  
Phone: +91 98765 43210  
Date of Birth: 15 March 2000  

----------------------------------------

Objective:
Motivated and detail-oriented individual seeking an entry-level position to utilize skills and grow professionally.

----------------------------------------

Education:
Bachelor of Science in Computer Science  
XYZ University, Kerala  
2021 – 2024  

Higher Secondary (12th Grade)  
ABC Higher Secondary School  
2019 – 2021  

Secondary School (10th Grade)  
ABC High School  
2018 – 2019  

----------------------------------------

Skills:
- Basic Programming (Python, Java)  
- MS Office (Word, Excel, PowerPoint)  
- Communication Skills  
- Teamwork and Problem Solving  

----------------------------------------

Experience:
Fresher

----------------------------------------

Declaration:
I hereby declare that the information provided above is true and correct to the best of my knowledge.

----------------------------------------

Place: Cochin  
Date: 22 June 2026  

Signature:  
Ananya Sharma"""

lexer= Lexer()
tokens = lexer.tokenize(txt)

parser=Parser(tokens,txt)
ast = parser.parse()

print(ast.model_dump_json(indent=2))