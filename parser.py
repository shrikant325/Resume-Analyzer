"""
Resume parser: turns raw extracted text into a structured dictionary using
regex-based field extraction (name / email / phone / links), section
detection, and dictionary-based skill extraction against the skill taxonomy.

A dictionary + regex approach is used instead of a statistical NER model so
this works reliably with zero extra downloads while remaining easy to reason
about and extend (this trade-off is documented in the README).
"""

import re

from app.nlp.skills_data import ALL_SKILLS, SKILL_ALIASES

EMAIL_RE = re.compile(r"[\w.\-+]+@[\w\-]+\.[\w.\-]+")
PHONE_RE = re.compile(r"(?:\+?\d{1,3}[\s\-]?)?(?:\(?\d{2,4}\)?[\s\-]?)?\d{3,4}[\s\-]?\d{3,4}")
LINKEDIN_RE = re.compile(r"(?:https?://)?(?:www\.)?linkedin\.com/[^\s,)]+", re.I)
GITHUB_RE = re.compile(r"(?:https?://)?(?:www\.)?github\.com/[^\s,)]+", re.I)

SECTION_HEADERS = {
    "education": ["education", "academic background", "academic qualification", "academic qualifications", "qualifications"],
    "experience": ["experience", "work experience", "professional experience", "employment history", "work history"],
    "internship": ["internship", "internships"],
    "projects": ["projects", "academic projects", "personal projects", "key projects"],
    "skills": ["skills", "technical skills", "core competencies", "key skills", "skill set"],
    "certifications": ["certifications", "certificates", "licenses", "certifications & courses"],
    "achievements": ["achievements", "awards", "honors", "achievements & awards"],
    "summary": ["summary", "objective", "profile", "career objective", "professional summary"],
}

# Ranked from lowest to highest so we can compare with `>=`.
DEGREE_KEYWORDS = {
    1: ["diploma", "associate degree", "polytechnic"],
    2: ["bachelor", "b.tech", "btech", "b.sc", "bsc", "b.e.", " be ", "bca", "b.com", "bcom", "undergraduate", "b.a.", "ba "],
    3: ["master", "m.tech", "mtech", "m.sc", "msc", "mba", "m.s.", " ms ", "postgraduate", "pg diploma", "m.com", "mcom", "m.a."],
    4: ["phd", "ph.d", "doctorate", "doctoral"],
}

WORD_RE = re.compile(r"\S+")


def _clean_header(line):
    return re.sub(r"[:\-•#*]+$", "", line.strip().lower()).strip()


def _find_sections(lines):
    """Split resume lines into named sections based on common headers."""
    sections = {"header": []}
    current = "header"
    for line in lines:
        stripped = line.strip()
        lower = _clean_header(stripped)
        matched = None
        if 0 < len(lower) < 40:
            for key, headers in SECTION_HEADERS.items():
                if lower in headers:
                    matched = key
                    break
        if matched:
            current = matched
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(line)
    return sections


def extract_name(lines):
    for line in lines[:8]:
        stripped = line.strip()
        if not stripped or len(stripped) > 40:
            continue
        if EMAIL_RE.search(stripped) or PHONE_RE.search(stripped) or "http" in stripped.lower():
            continue
        words = [w for w in stripped.split() if w.isalpha()]
        if 1 < len(words) <= 4 and len(words) == len(stripped.split()):
            if all(w[0].isupper() for w in words):
                return stripped
    return None


def extract_contact(text):
    email_match = EMAIL_RE.search(text)
    phone_match = PHONE_RE.search(text)
    linkedin_match = LINKEDIN_RE.search(text)
    github_match = GITHUB_RE.search(text)
    return {
        "email": email_match.group(0) if email_match else None,
        "phone": phone_match.group(0).strip() if phone_match else None,
        "linkedin": linkedin_match.group(0) if linkedin_match else None,
        "github": github_match.group(0) if github_match else None,
    }


def extract_skills(text):
    """Dictionary-based skill extraction: match whole-word occurrences of
    every known skill (and its aliases) in the given text."""
    if not text:
        return []
    text_lower = text.lower()
    found = set()
    for skill in ALL_SKILLS:
        pattern = r"(?<![a-zA-Z0-9])" + re.escape(skill.lower()) + r"(?![a-zA-Z0-9])"
        if re.search(pattern, text_lower):
            found.add(skill)
    for alias, canonical in SKILL_ALIASES.items():
        pattern = r"(?<![a-zA-Z0-9])" + re.escape(alias) + r"(?![a-zA-Z0-9])"
        if re.search(pattern, text_lower):
            found.add(canonical)
    return sorted(found)


def extract_education_level(text):
    text_lower = " " + text.lower() + " "
    best_level = 0
    matched_keyword = None
    for level, keywords in DEGREE_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower and level > best_level:
                best_level = level
                matched_keyword = kw.strip()
    return {"level": best_level, "matched_keyword": matched_keyword}


def extract_experience_years(text):
    matches = re.findall(r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years|yrs|year)\b", text.lower())
    years = [float(m) for m in matches if float(m) <= 50]
    return max(years) if years else None


def count_measurable_achievements(lines):
    count = 0
    for line in lines:
        if re.search(r"\d+%|\$\s?\d+|\d+x\b|\bby \d+\b|\d{2,}\+", line):
            count += 1
    return count


def parse_resume(text):
    text = text or ""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    sections = _find_sections(lines)
    contact = extract_contact(text)
    name = extract_name(lines)
    skills = extract_skills(text)
    education = extract_education_level(text)
    experience_years = extract_experience_years(text)
    achievements = count_measurable_achievements(lines)
    sections_found = [key for key, body in sections.items() if key != "header" and body]

    return {
        "name": name,
        "email": contact["email"],
        "phone": contact["phone"],
        "linkedin": contact["linkedin"],
        "github": contact["github"],
        "skills": skills,
        "education_level": education["level"],
        "education_keyword": education["matched_keyword"],
        "experience_years": experience_years,
        "sections_found": sections_found,
        "measurable_achievements": achievements,
        "word_count": len(WORD_RE.findall(text)),
        "raw_sections": {k: "\n".join(v) for k, v in sections.items()},
    }
