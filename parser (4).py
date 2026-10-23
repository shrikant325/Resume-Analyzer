"""
Job description parser: extracts required/preferred skills, education and
experience requirements, and top TF-IDF keywords from a pasted JD.
"""

from sklearn.feature_extraction.text import TfidfVectorizer

from app.nlp.preprocess import STOP_WORDS
from app.resume.parser import extract_skills, extract_education_level, extract_experience_years

PREFERRED_MARKERS = [
    "preferred qualifications", "preferred skills", "nice to have", "nice-to-have",
    "good to have", "bonus points", "bonus if", "a plus", "preferred",
]

# Headings that end a "preferred skills" block even without a blank line,
# so unrelated content (responsibilities, benefits...) after it isn't
# mistaken for a preferred skill.
SECTION_BOUNDARY_MARKERS = [
    "requirements:", "required qualifications", "responsibilities:", "qualifications:",
    "about the company", "about us", "benefits:", "how to apply", "what we offer",
    "duties:", "role:", "job description:",
]


def _split_required_preferred(text):
    """Best-effort split: text between the first 'preferred/nice-to-have'
    marker and the next section heading is treated as preferred; everything
    else stays required."""
    lower = text.lower()
    positions = [lower.find(marker) for marker in PREFERRED_MARKERS if marker in lower]
    if not positions:
        return text, ""
    start = min(positions)

    search_from = start + 10
    end_candidates = [
        lower.find(marker, search_from) for marker in SECTION_BOUNDARY_MARKERS
        if lower.find(marker, search_from) != -1
    ]
    end = min(end_candidates) if end_candidates else len(text)

    preferred_text = text[start:end]
    required_text = text[:start] + text[end:]
    return required_text, preferred_text


def extract_keywords(text, top_n=15):
    """Top TF-IDF keywords, kept as whole (unstemmed) words on purpose: these
    are shown directly in the UI and matched as substrings against resume
    text, so they need to stay real, readable words rather than stems."""
    if not text or not text.strip():
        return []
    # sklearn tokenizes before comparing against stop_words, so strip
    # apostrophes here too (e.g. "aren't" -> "arent") to avoid a mismatch.
    sklearn_stopwords = sorted({w.replace("'", "") for w in STOP_WORDS})
    vectorizer = TfidfVectorizer(
        max_features=100,
        stop_words=sklearn_stopwords,
        token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z\-]+\b",
    )
    try:
        matrix = vectorizer.fit_transform([text.lower()])
    except ValueError:
        return []
    scores = matrix.toarray()[0]
    terms = vectorizer.get_feature_names_out()
    ranked = sorted(zip(terms, scores), key=lambda pair: pair[1], reverse=True)
    return [term for term, score in ranked[:top_n] if score > 0]


def parse_job_description(text):
    text = text or ""
    required_text, preferred_text = _split_required_preferred(text)

    required_skills = extract_skills(required_text)
    preferred_skills = extract_skills(preferred_text) if preferred_text else []
    preferred_skills = [s for s in preferred_skills if s not in required_skills]

    if not required_skills and not preferred_skills:
        # No clear split found anywhere - treat every detected skill as required.
        required_skills = extract_skills(text)

    all_skills = sorted(set(required_skills) | set(preferred_skills))

    education = extract_education_level(text)
    experience_years = extract_experience_years(text)
    keywords = extract_keywords(text)

    return {
        "required_skills": required_skills,
        "preferred_skills": preferred_skills,
        "all_skills": all_skills,
        "education_level": education["level"],
        "education_keyword": education["matched_keyword"],
        "experience_years_required": experience_years,
        "keywords": keywords,
    }
