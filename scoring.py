"""
Education/experience sub-scores and the final weighted compatibility score.
"""


def compute_education_match(resume_level, jd_level):
    """Levels: 0=none/unspecified, 1=diploma, 2=bachelor, 3=master, 4=phd."""
    if not jd_level:
        return 100.0
    resume_level = resume_level or 0
    if resume_level >= jd_level:
        return 100.0
    if resume_level == jd_level - 1:
        return 60.0
    return 30.0


def compute_experience_match(resume_years, jd_years):
    if not jd_years:
        return 100.0
    if resume_years is None:
        return 40.0
    if resume_years >= jd_years:
        return 100.0
    ratio = resume_years / jd_years
    return round(max(30.0, ratio * 100), 2)


def compute_compatibility_score(skill_match_score, keyword_match_score, semantic_score,
                                 education_match_score, experience_match_score, weights):
    total = (
        skill_match_score * weights["skill"]
        + keyword_match_score * weights["keyword"]
        + semantic_score * weights["semantic"]
        + education_match_score * weights["education"]
        + experience_match_score * weights["experience"]
    )
    return round(total, 2)


def score_interpretation(score):
    if score >= 80:
        return "Excellent Match"
    if score >= 65:
        return "Good Match"
    if score >= 50:
        return "Moderate Match"
    if score >= 30:
        return "Low Match"
    return "Poor Match"
