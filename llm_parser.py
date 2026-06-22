# LLM integration

# llm_parser.py
class LLMParser:
    def __init__(self, api_key: str, model: str = "gpt-4o-mini")
    def parse_with_llm(self, resume_text: str) -> ResumeData
    def _build_prompt(self, resume_text: str) -> str