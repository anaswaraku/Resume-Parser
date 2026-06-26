from utils.key_words import SECTION_KW
 

l = ["OBJECTIVE","SUMMARY","Career Objective","Education","Education Section","Course","Related Course Work","ACADEMIC DEGREES","Academic Profile","Education","Academic Details","Academic Background","Qualifications"," Academic History","Skills","Technical Skills","Transferable Skills","Computer Skills","Technical Skills","Skills","Tech Stack","Core Competencies","Coding Skills", "Development Skills","RESEARCH INTERESTS & COMPUTER SKILLS","RESEARCH INTERESTS","COMPUTER SKILLS","Experience","Experiences","Work","Experience","Related Experience","Internship","Internships","RELEVANT EXPERIENCE","RELEVANT Experiences","INDUSTRY EXPERIENCE","INDUSTRY Experiences","OTHER EXPERIENCE","OTHER Experiences","RESEARCH EXPERIENCE","Experience","Work Experience"," Internships", "Professional","Experience","Career", "Job","Internships","RESEARCH Experiences","EMPLOYMENT","PREVIOUS EMPLOYMENT","PUBLICATIONS","Project","SENIOR PROJECT","Projects & Work Done","Activities","Leader","Leadership","Activities and Honors","MEMBERSHIPS","WORKSHOPS","COURSES","RELATED WORKSHOPS","Extra-curricular Activities","Extra co-curricular Activities","Extra co curricular Activities","Interests"," CURRICULUM VITAE", "Extra-Curricular Activities","Extra-Curricular Activities","Activities","Interests","Certifications","Certifications","Licenses","Courses","Leadership", "Leadership","Leadership Experience","Roles & Responsibilities"]

u=[]
for i in l:
    i=i.upper().strip()
    u.append(i)
#print(set(u))

new=[]
all_dict_values=set(value.strip() for sublist in SECTION_KW.values() for value in sublist)
missing = [item.upper() for item in u if item not in all_dict_values]
print(missing)