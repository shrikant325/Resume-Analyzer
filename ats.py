"""
ATS-style resume analyzer. Produces a 0-100 score built from six weighted,
explainable checks so the reasoning can be shown to the user (spec section
10 & 21: ATS score + reasons / explainability).
"""

import re
from collections import Counter

EXPECTED_SECTIONS = {"education", "experience", "skills", "projects"}


def compute_ats_score(resume_parsed, resume_text, jd_keywords):
    checks = []
    score = 0.0
    max_score = 0.0
    resume_text = resume_text or ""

    # 1. Contact information (15 pts)
    max_score += 15
    contact_points = 0
    if resume_parsed.get("email"):
        contact_points += 8
    if resume_parsed.get("phone"):
        contact_points += 7
    score += contact_points
    checks.append({
        "label": "Contact information present",
        "passed": contact_points >= 8,
        "detail": "Email and phone number detected." if contact_points == 15
        else ("Only partial contact info detected." if contact_points else "No email or phone number detected."),
    })

    # 2. Standard resume sections (25 pts)
    max_score += 25
    found_sections = set(resume_parsed.get("sections_found", []))
    overlap = EXPECTED_SECTIONS & found_sections
    section_points = round(len(overlap) / len(EXPECTED_SECTIONS) * 25)
    score += section_points
    checks.append({
        "label": "Standard resume sections",
        "passed": section_points >= 15,
        "detail": f"Detected: {', '.join(sorted(found_sections)).title() or 'none'}.",
    })

    # 3. Job-specific keyword coverage (25 pts)
    max_score += 25
    if jd_keywords:
        resume_lower = resume_text.lower()
        present = sum(1 for kw in jd_keywords if kw.lower() in resume_lower)
        keyword_points = round(present / len(jd_keywords) * 25)
    else:
        keyword_points = 20
    score += keyword_points
    checks.append({
        "label": "Job-specific keywords present",
        "passed": keyword_points >= 15,
        "detail": f"{keyword_points}/25 points from keyword coverage against the job description.",
    })

    # 4. Measurable achievements (15 pts)
    max_score += 15
    achievements = resume_parsed.get("measurable_achievements", 0)
    achievement_points = min(15, achievements * 3)
    score += achievement_points
    checks.append({
        "label": "Measurable achievements",
        "passed": achievements >= 2,
        "detail": f"{achievements} quantified statement(s) detected (numbers, %, $ etc).",
    })

    # 5. Resume length (10 pts)
    max_score += 10
    word_count = resume_parsed.get("word_count", 0)
    if 250 <= word_count <= 900:
        length_points = 10
    elif 150 <= word_count < 250 or 900 < word_count <= 1200:
        length_points = 6
    else:
        length_points = 3
    score += length_points
    checks.append({
        "label": "Appropriate resume length",
        "passed": length_points >= 6,
        "detail": f"{word_count} words.",
    })

    # 6. No excessive repetition (10 pts)
    max_score += 10
    words = re.findall(r"[a-zA-Z]{4,}", resume_text.lower())
    if words:
        counts = Counter(words)
        _most_common_word, most_common_count = counts.most_common(1)[0]
        repetition_ratio = most_common_count / len(words)
        if repetition_ratio < 0.04:
            repetition_points = 10
        elif repetition_ratio < 0.07:
            repetition_points = 5
        else:
            repetition_points = 2
    else:
        repetition_points = 5
    score += repetition_points
    checks.append({
        "label": "No excessive keyword repetition",
        "passed": repetition_points >= 5,
        "detail": "Word usage looks natural." if repetition_points == 10 else "Some repeated phrasing detected.",
    })

    final_score = round(score / max_score * 100, 2) if max_score else 0.0
    return {"ats_score": final_score, "checks": checks}
