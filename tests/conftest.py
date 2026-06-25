"""
Shared pytest fixtures for the resume-parser test suite.
"""

import pytest
from ast_models import Education, Experience, ResumeAST
from llm_parser import ResumeData


SAMPLE_RESUME_TEXT = """\
John Doe
john.doe@example.com
123-456-7890

Education
BSc Computer Science
XYZ University
Jan 2018 - May 2022

Experience
Acme Corp
Software Engineer
Jun 2022 - Present
Built REST APIs and maintained CI/CD pipelines.

Skills
Python, FastAPI, Docker, SQL
"""


@pytest.fixture
def sample_text() -> str:
    return SAMPLE_RESUME_TEXT


@pytest.fixture
def sample_ast() -> ResumeAST:
    return ResumeAST(
        name="John Doe",
        email="john.doe@example.com",
        phone="123-456-7890",
        education=[Education(degree="BSc Computer Science", school="XYZ University",
                             start_date="Jan 2018", end_date="May 2022")],
        experience=[Experience(company="Acme Corp", role="Software Engineer",
                               start_date="Jun 2022", end_date="Present",
                               description="Built REST APIs.")],
        skills=["Python", "FastAPI", "Docker", "SQL"],
    )


@pytest.fixture
def sample_llm_data() -> ResumeData:
    return ResumeData(
        name="John Doe",
        email="john.doe@example.com",
        phone="123-456-7890",
        education=[Education(degree="BSc Computer Science", school="XYZ University",
                             start_date="2018-01", end_date="2022-05")],
        experience=[Experience(company="Acme Corp", role="Software Engineer",
                               start_date="2022-06", end_date=None,
                               description="Built REST APIs.")],
        skills=["Python", "FastAPI", "Docker", "SQL", "Git"],
    )


@pytest.fixture
def empty_ast() -> ResumeAST:
    return ResumeAST()


@pytest.fixture
def empty_llm_data() -> ResumeData:
    return ResumeData()
