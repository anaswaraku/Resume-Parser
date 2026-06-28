import sys
import os

# Ensure the root project directory is in the Python path
# so that modules like 'main' and 'lexer' can be imported easily
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
