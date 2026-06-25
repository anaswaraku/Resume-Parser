from typing import List

_SYNONYMS: dict[str, str] = { # Alias -> Canonical Form
    # Languages
    "js":       "javascript",
    "ts":       "typescript",
    "py":       "python",
    "rb":       "ruby",
    "golang":   "go",
    # Cloud
    "amazon web services": "aws",
    "gcp":          "google cloud platform",
    "google cloud": "google cloud platform",
    "azure":        "microsoft azure",
    # ML / AI
    "ml":     "machine learning",
    "dl":     "deep learning",
    "ai":     "artificial intelligence",
    "nlp":    "natural language processing",
    "cv":     "computer vision",
    "gen ai": "generative ai",
    "unsupervised ml": "machine learning",
    "supervised ml":   "machine learning",
    "llm":    "large language model",
    # DevOps
    "k8s":    "kubernetes",
    "ci/cd":  "continuous integration",
    "ci cd":  "continuous integration",
    # Frameworks / libs
    "react":      "reactjs",
    "react.js":   "reactjs",
    "react js":   "reactjs",
    "vue":        "vuejs",
    "vue.js":     "vuejs",
    "node":       "nodejs",
    "node.js":    "nodejs",
    "next":       "nextjs",
    "next.js":    "nextjs",
    "express":    "expressjs",
    "express.js": "expressjs",
    "fast api":   "fastapi",
    "spring":     "spring boot",
    # Databases
    "postgres": "postgresql",
    "mongo":    "mongodb",
    "es":       "elasticsearch",
    # Practices
    "oop":     "object oriented programming",
    "tdd":     "test driven development",
    "bdd":     "behavior driven development",
    "rest":    "rest api",
    "restful": "rest api",
    "graphql": "graphql api",
    # Misc
    "dot net": ".net",
    "dotnet":  ".net",
    "asp.net": ".net",
    "tf":      "tensorflow",
    "pt":      "pytorch",

    # Google Cloud
    "bigquery": "google bigquery",
    "cloud composer": "google cloud composer",
    "dataflow": "google cloud dataflow",
    "pub/sub": "google cloud pub/sub",
    "cloud functions": "google cloud functions",
    "dataproc": "google cloud dataproc",
    "cloud storage": "google cloud storage",
    "cloud build": "google cloud build",

    # ETL
    "elt": "etl",
    "etl / elt": "etl",
    "extract, transform, load": "etl",

    # Communication
    "communication skills": "communication",
    "verbal communication": "communication",
    "written communication": "communication",
    "oral communication": "communication",
    "effective communication": "communication",
    "presentation skills": "presentation",
    "public speaking": "presentation",
    "storytelling": "presentation",
    "technical writing": "writing",
    "business writing": "writing",
    "documentation": "writing",
    "active listening": "listening",
    "listening skills": "listening",

    # Leadership
    "leadership skills": "leadership",
    "team leadership": "leadership",
    "leading teams": "leadership",
    "people management": "leadership",
    "mentorship": "mentoring",
    "mentoring": "mentoring",
    "coaching": "mentoring",
    "team management": "people management",
    "stakeholder management": "stakeholder management",

    # Teamwork
    "team player": "teamwork",
    "teamwork skills": "teamwork",
    "team collaboration": "collaboration",
    "cross functional collaboration": "collaboration",
    "cross-functional collaboration": "collaboration",
    "collaborative": "collaboration",
    "working with teams": "teamwork",

    # Problem Solving
    "problem solving skills": "problem solving",
    "analytical thinking": "analytical skills",
    "critical thinking": "critical thinking",
    "logical thinking": "critical thinking",
    "decision making": "decision making",
    "decision-making": "decision making",
    "troubleshooting": "problem solving",
    "root cause analysis": "problem solving",

    # Adaptability
    "adaptability skills": "adaptability",
    "adaptable": "adaptability",
    "flexibility": "adaptability",
    "agility": "adaptability",
    "resilience": "resilience",
    "learning agility": "learning agility",
    "continuous learning": "continuous learning",
    "quick learner": "fast learner",
    "fast learner": "fast learner",
    "self learner": "self learning",
    "self-learning": "self learning",

    # Time & Organization
    "time management skills": "time management",
    "prioritization": "prioritization",
    "priority management": "prioritization",
    "organizational skills": "organization",
    "organization skills": "organization",
    "planning": "planning",
    "planning skills": "planning",
    "multitasking": "multi-tasking",
    "multi tasking": "multi-tasking",

    # Work Ethic
    "ownership": "ownership",
    "accountability": "accountability",
    "responsibility": "accountability",
    "self motivated": "self motivation",
    "self-motivated": "self motivation",
    "initiative": "initiative",
    "proactive": "proactiveness",
    "proactiveness": "proactiveness",
    "dedication": "commitment",
    "committed": "commitment",
    "commitment": "commitment",
    "reliability": "reliability",
    "dependability": "reliability",
    "professionalism": "professionalism",

    # Interpersonal
    "interpersonal skills": "interpersonal skills",
    "relationship building": "relationship management",
    "relationship management": "relationship management",
    "networking": "networking",
    "emotional intelligence": "emotional intelligence",
    "eq": "emotional intelligence",
    "empathy": "empathy",
    "conflict resolution": "conflict management",
    "conflict management": "conflict management",
    "negotiation": "negotiation",
    "persuasion": "persuasion",

    # Customer / Business
    "customer service": "customer service",
    "customer support": "customer service",
    "customer success": "customer success",
    "client management": "client relationship management",
    "client relationship management": "client relationship management",
    "stakeholder communication": "stakeholder management",

    # Creativity
    "creative thinking": "creativity",
    "innovation": "innovation",
    "innovative thinking": "innovation",
    "design thinking": "design thinking",
    "brainstorming": "ideation",
    "ideation": "ideation",

    # Quality
    "attention to detail": "attention to detail",
    "detail oriented": "attention to detail",
    "detail-oriented": "attention to detail",
    "quality focused": "quality assurance mindset",
    "quality mindset": "quality assurance mindset",

    # Business
    "business acumen": "business acumen",
    "commercial awareness": "business acumen",
    "strategic thinking": "strategic thinking",
    "strategic planning": "strategic thinking",

    # Agile
    "agile mindset": "agile mindset",
    "scrum master skills": "scrum",
    "facilitation": "facilitation",

    # Misc
    "positive attitude": "positive attitude",
    "growth mindset": "growth mindset",
    "work under pressure": "stress management",
    "stress management": "stress management",
    "remote collaboration": "remote teamwork",
    "virtual collaboration": "remote teamwork",
    "remote teamwork": "remote teamwork",
    "cultural awareness": "cross-cultural communication",
    "cross cultural communication": "cross-cultural communication"

}


#Keyword extraction fallback 

_STOP: set[str] = {
    # ── Standard English stop words ───────────────────────────────────────────
    "a", "about", "ability", "above", "academic", "achievements", "activities",
    "after", "again", "all", "also", "am", "an", "and", "analytical", "any",
    "applications", "apply", "are", "as", "at", "background", "be",
    "because", "been", "before", "being", "below", "benefits", "between",
    "both", "build", "but", "by", "can", "candidate", "cannot",
    "company", "competencies", "concepts", "consider", "core", "could",
    "current", "daily", "department", "description", "design",
    "develop", "did", "do", "does", "doing", "domain",
    "down", "during", "duties", "each", "education", "employment",
    "etc", "excellent", "experience", "experienced", "expertise", "extra",
    "familiar", "few", "for", "frameworks", "from", "full-time", "further",
    "good", "graduate", "had", "has", "have", "having", "he", "her", "here",
    "hers", "herself", "him", "himself", "his", "history", "how", "i",
    "ideal", "if", "implement", "in", "including",
    "industry", "information", "internship", "into", "is", "it",
    "its", "itself", "job", "join", "just", "key", "knowledge",
    "languages", "level", "like", "location", "locations", "looking",
    "manage", "me", "members", "minimum", "miscellaneous", "more", "most",
    "must", "my", "myself", "needed", "new", "no", "nor", "not",
    "now", "of", "off", "on", "once", "only", "operate", "opportunity", "or",
    "other", "ought", "our", "ours", "ourselves", "out", "over", "overview",
    "own", "perform", "plus", "position", "preferred", "prepare", "principles",
    "problem", "professional", "proficiency", "proficient", "projects",
    "provide", "qualifications", "required", "requirement", "requirements",
    "responsibilities", "role", "roles", "salary", "same", "science", "seeking",
    "senior", "she", "should", "similar", "skill", "skills", "so", "solid",
    "some", "solving", "strong", "such", "summary", "support", "systems", "team",
    "technical", "technologies", "than", "that", "the", "their", "theirs", "them",
    "themselves", "then", "there", "these", "they", "this", "those", "through",
    "to", "too", "tools", "top", "type", "under", "understanding", "university",
    "until", "up", "use", "used", "using", "various", "very", "was", "we",
    "were", "what", "when", "where", "which", "while", "who", "whom", "why",
    "will", "with", "work", "working", "world", "would", "year", "years",
    "you", "your", "yours", "yourself", "yourselves",
    # ── JD structural / boilerplate words ────────────────────────────────────
    "posted", "since", "organization", "field", "employment", "type",
    "mode", "hybrid", "onsite", "office", "site", "full", "time",
    "part", "contract", "permanent", "temporary", "fresher",
    "accelerated", "across", "advantage", "agentic", "applying",
    "approach", "architecture", "broadly", "cars", "ships",
    "manufacture", "manufactured", "many", "skyscrapers",
    # ── Indian city / state / location names ─────────────────────────────────
    "india", "pune", "maharashtra", "mumbai", "bangalore", "bengaluru",
    "hyderabad", "chennai", "delhi", "noida", "gurugram", "gurgaon",
    "kochi", "thrissur", "kerala", "karnataka", "tamil",
    # ── Company / legal entity noise ─────────────────────────────────────────
    "private", "limited", "pvt", "ltd", "inc", "corp", "llc",
    # ── Month abbreviations (appear in "Posted since Jun-2026" etc.) ─────────
    "jan", "feb", "mar", "apr", "jun", "jul", "aug",
    "sep", "oct", "nov", "dec",
    # Full month names
    "january", "february", "march", "april", "june", "july", "august",
    "september", "october", "november", "december",
    # Other common JD noise missed above
    "need", "needs", "help", "take", "takes", "get", "make", "makes",
    "see", "keep", "give", "know", "find", "based",
}



_MULTI_WORD_SKILLS: List[str] = sorted(
    list(
        {
            s
            for s in list(_SYNONYMS.keys()) + list(_SYNONYMS.values())
            if " " in s
        }
    ),
    key=len,
    reverse=True,
)