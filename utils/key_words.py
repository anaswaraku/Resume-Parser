SECTION_KW = {
    'SUMMARY': [
        'CAREER OBJECTIVE',
        'CAREER SUMMARY',
        'OBJECTIVE',
        'PERSONAL PROFILE',
        'PROFESSIONAL SUMMARY',
        'PROFILE',
        'SUMMARY'
    ],
    'EDUCATION': [
        'ACADEMIC BACKGROUND',
        'ACADEMIC DEGREES',
        'ACADEMIC DETAILS',
        'ACADEMIC HISTORY',
        'ACADEMIC PROFILE',
        'COURSE',
        'EDUCATION',
        'EDUCATION SECTION',
        'EDUCATIONAL QUALIFICATIONS',
        'QUALIFICATIONS',
        'RELATED COURSE WORK'
    ],
    'SKILLS': [
        'AREAS OF EXPERTISE',
        'CODING SKILLS',
        'COMPUTER SKILLS',
        'CORE COMPETENCIES',
        'DEVELOPMENT SKILLS',
        'PROFICIENCIES',
        'PROFESSIONAL SKILLS',
        'RESEARCH INTERESTS',
        'RESEARCH INTERESTS & COMPUTER SKILLS',
        'SKILLS',
        'TECHNICAL SKILLS',
        'TECH STACK',
        'TRANSFERABLE SKILLS'
    ],
    'EXPERIENCES': [
        'CAREER',
        'EMPLOYMENT',
        'EMPLOYMENT HISTORY',
        'EXPERIENCE',
        'EXPERIENCES',
        'INDUSTRY EXPERIENCE',
        'INTERNSHIP',
        'INTERNSHIPS',
        'JOB',
        'OTHER EXPERIENCE',
        'PREVIOUS EMPLOYMENT',
        'PROFESSIONAL',
        'PROFESSIONAL EXPERIENCE',
        'RELATED EXPERIENCE',
        'RELEVANT EXPERIENCE',
        'RESEARCH EXPERIENCE',
        'WORK',
        'WORK EXPERIENCE',
        'WORK HISTORY'
    ],
    'PROJECTS': [
        'ACADEMIC PROJECTS',
        'PERSONAL PROJECTS',
        'PROJECT',
        'PROJECTS',
        'PROJECTS & WORK DONE',
        'SENIOR PROJECT'
    ],
    'ACHIEVEMENTS': [
        'ACCOMPLISHMENTS',
        'ACHIEVEMENTS',
        'AWARDS',
        'AWARDS & HONORS',
        'HONORS'
    ],
    'CERTIFICATIONS': [
        'CERTIFICATIONS',
        'COURSES',
        'LICENSES',
        'LICENSES & CERTIFICATIONS',
        'PROFESSIONAL DEVELOPMENT',
        'TRAINING'
    ],
    'LEADERSHIP': [
        'LEADERSHIP',
        'LEADERSHIP EXPERIENCE',
        'ROLES & RESPONSIBILITIES'
    ],
    'EXTRA-CURRICULAR ACTIVITIES': [
        'ACTIVITIES',
        'ACTIVITIES AND HONORS',
        'CO-CURRICULAR ACTIVITIES',
        'EXTRA CO CURRICULAR ACTIVITIES',
        'EXTRA CO-CURRICULAR ACTIVITIES',
        'INTERESTS',
        'MEMBERSHIPS',
        'RELATED COURSES',
        'RELATED WORKSHOPS',
        'WORKSHOPS'
    ],
    'PUBLICATIONS': [
        'PUBLICATIONS',
        'RESEARCH PAPER',
        'RESEARCH PAPERS'
    ],
    'ADDITIONAL INFORMATION': [
        'ADDITIONAL INFORMATION',
        'ADDITIONAL NOTES',
        'MISCELLANEOUS'
    ],
    'REFERENCES': [
        'REFEREES',
        'REFERENCES'
    ]
}

w="""def parse(self,sections):
        result = [
            ParsedSection(
                header=section.header,
                raw=section.raw
            )for section in sections
        ]
        return result
"""