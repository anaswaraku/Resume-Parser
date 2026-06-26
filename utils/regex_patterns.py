import re

# Shared regular expression components for dates
MONTH_STR = r'(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec|0?[1-9]|1[0-2])'
YEAR_STR = r'(?:19|20)\d{2}'
SEP_STR = r'[\s\-/\.,]+'
RANGE_SEP_STR = r'[\s\-–—to]+'
PRESENT_STR = r'(?:present|current|now)'

# Compiled patterns for direct use in parsers
# Note: SEP_STR is optional to handle dates like "May2024"
DATE_RANGE_RE = re.compile(fr'(?i)\b{MONTH_STR}\.?{SEP_STR}?{YEAR_STR}{RANGE_SEP_STR}(?:{MONTH_STR}\.?{SEP_STR}?{YEAR_STR}|{PRESENT_STR})\b')
YEAR_RANGE_RE = re.compile(fr'(?i)\b{YEAR_STR}{RANGE_SEP_STR}(?:{YEAR_STR}|\d{{2}}|{PRESENT_STR})\b')
DATE_RE = re.compile(fr'(?i)\b{MONTH_STR}\.?{SEP_STR}?{YEAR_STR}\b')
YEAR_RE = re.compile(fr'\b{YEAR_STR}\b')
