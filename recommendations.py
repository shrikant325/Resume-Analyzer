"""
Resume improvement suggestions, job-specific skill recommendations, and the
"why this score" explainability block (spec sections 11, 12, 13, 21).
"""

import re

WEAK_STARTS = (
    "made ", "did ", "worked on ", "helped ", "was responsible for ", "handled ",
    "used ", "involved in ", "tasked with ", "responsible for ",
)


def _weak_lines(section_text):
    lines = [ln.strip() for ln in (section_text or "").splitlines() if ln.strip()]
    weak = []
    for line in lines:
        if not (10 < len(line) < 220):
            continue
        lower = line.lower().lstrip("-•*0123456789. ")
        has_number = bool(re.search(r"\d", line))
        starts_weak = any(lower.startswith(w) for w in WEAK_STARTS)
        if starts_weak and not has_number:
            weak.append(line)
    return weak[:5]


def generate_improvement_suggestions(resume_parsed, ats_result, skill_gap):
    suggestions = []
    raw_sections = resume_parsed.get("raw_sections", {})
    combined = (raw_sections.get("experience", "") + "\n" + raw_sections.get("projects", "") + "\n"
                + raw_sections.get("internship", ""))

    for line in _weak_lines(combined):
        snippet = line if len(line) <= 90 else line[:87] + "..."
        suggestions.append({
            "type": "weak_description",
            "priority": "High",
            "text": f'This line reads as vague — strengthen it with an action verb and a measurable '
                    f'result: "{snippet}"',
        })

    if resume_parsed.get("measurable_achievements", 0) < 2:
        suggestions.append({
            "type": "measurable_achievements",
            "priority": "High",
            "text": "Add measurable achievements to your experience and project bullets "
                    "(e.g. 'reduced page load time by 30%' or 'served 500+ users') instead of "
                    "plain task descriptions.",
        })

    if skill_gap.get("missing"):
        top_missing = ", ".join(skill_gap["missing"][:5])
        suggestions.append({
            "type": "missing_keywords",
            "priority": "High",
            "text": f"Work these job-specific keywords/skills into your resume where truthful: {top_missing}.",
        })

    found_sections = set(resume_parsed.get("sections_found", []))
    for section in ("education", "experience", "skills", "projects"):
        if section not in found_sections:
            suggestions.append({
                "type": "missing_section",
                "priority": "Medium",
                "text": f"No clear '{section.title()}' section was detected — add one with an explicit heading "
                        f"so both humans and ATS software can find it.",
            })

    word_count = resume_parsed.get("word_count", 0)
    if word_count and word_count < 150:
        suggestions.append({
            "type": "too_short",
            "priority": "Medium",
            "text": "Your resume looks quite short. Add more detail about your projects, "
                    "responsibilities, and outcomes.",
        })
    elif word_count > 1200:
        suggestions.append({
            "type": "too_long",
            "priority": "Low",
            "text": "Your resume is quite long. Trim less relevant details to keep it focused, "
                    "ideally to one or two pages.",
        })

    if not resume_parsed.get("email") or not resume_parsed.get("phone"):
        suggestions.append({
            "type": "missing_contact",
            "priority": "High",
            "text": "Make sure your email and phone number are clearly visible near the top of your resume.",
        })

    if not resume_parsed.get("skills"):
        suggestions.append({
            "type": "no_skills_detected",
            "priority": "Medium",
            "text": "No recognizable technical skills were detected — add a dedicated 'Skills' section "
                    "listing your key tools and technologies.",
        })

    order = {"High": 0, "Medium": 1, "Low": 2}
    suggestions.sort(key=lambda s: order.get(s["priority"], 3))
    return suggestions


def generate_skill_recommendations(missing_skills_with_priority):
    order = {"High": 0, "Medium": 1, "Low": 2}
    recs = [{"skill": skill, "priority": priority} for skill, priority in missing_skills_with_priority.items()]
    recs.sort(key=lambda r: order.get(r["priority"], 3))
    return recs


def build_explainability(skill_result, education_ok, semantic_score):
    lines = []
    total_required = len(skill_result["matching"]) + len(skill_result["missing"])
    if total_required:
        lines.append({
            "positive": len(skill_result["missing"]) == 0,
            "text": f"{len(skill_result['matching'])}/{total_required} required skills matched",
        })
    else:
        lines.append({"positive": True, "text": "No specific required skills were detected in the job description"})

    lines.append({
        "positive": education_ok,
        "text": "Education requirement satisfied" if education_ok else "Education requirement may not be fully met",
    })

    lines.append({
        "positive": semantic_score >= 60,
        "text": "Strong overall content similarity to the job description" if semantic_score >= 60
        else "Limited overall content similarity to the job description",
    })

    for skill in skill_result["missing"][:4]:
        lines.append({"positive": False, "text": f"Missing {skill}"})

    if skill_result.get("additional"):
        lines.append({
            "positive": True,
            "text": f"{len(skill_result['additional'])} additional relevant skill(s) beyond the job's requirements",
        })

    return lines
