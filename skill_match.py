"""
Skill matching (resume vs. job description) and missing-skill prioritization.
"""

import re


def match_skills(resume_skills, required_skills, preferred_skills=None):
    preferred_skills = preferred_skills or []
    resume_set = set(resume_skills)
    required_set = set(required_skills)
    preferred_set = set(preferred_skills)

    matching = sorted(resume_set & required_set)
    missing = sorted(required_set - resume_set)
    matching_preferred = sorted(resume_set & preferred_set)
    missing_preferred = sorted(preferred_set - resume_set)
    additional = sorted(resume_set - required_set - preferred_set)

    skill_match_score = round(len(matching) / len(required_set) * 100, 2) if required_set else 100.0

    return {
        "matching": matching,
        "missing": missing,
        "matching_preferred": matching_preferred,
        "missing_preferred": missing_preferred,
        "additional": additional,
        "skill_match_score": skill_match_score,
    }


def prioritize_missing_skills(missing_skills, jd_text):
    """Rank missing skills High/Medium/Low based on how frequently and how
    early they appear in the job description (spec: 'priority should be
    determined based on how frequently or strongly the skill appears')."""
    if not missing_skills:
        return {}

    text_lower = (jd_text or "").lower()
    text_len = max(len(text_lower), 1)
    scored = {}
    for skill in missing_skills:
        pattern = r"(?<![a-zA-Z0-9])" + re.escape(skill.lower()) + r"(?![a-zA-Z0-9])"
        occurrences = re.findall(pattern, text_lower)
        freq = len(occurrences)
        first_match = re.search(pattern, text_lower)
        relative_position = (first_match.start() / text_len) if first_match else 1.0
        scored[skill] = freq * 2 + (1 - relative_position)

    ranked = sorted(scored.items(), key=lambda pair: pair[1], reverse=True)
    total = len(ranked)
    result = {}
    for index, (skill, _score) in enumerate(ranked):
        if index < max(1, round(total / 3)):
            result[skill] = "High"
        elif index < max(2, round(total * 2 / 3)):
            result[skill] = "Medium"
        else:
            result[skill] = "Low"
    return result


def keyword_match(resume_text, jd_keywords):
    if not jd_keywords:
        return {"matched": [], "missing": [], "keyword_match_score": 100.0}
    resume_lower = (resume_text or "").lower()
    matched = [kw for kw in jd_keywords if kw.lower() in resume_lower]
    missing = [kw for kw in jd_keywords if kw.lower() not in resume_lower]
    score = round(len(matched) / len(jd_keywords) * 100, 2)
    return {"matched": matched, "missing": missing, "keyword_match_score": score}
