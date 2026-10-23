"""
Orchestrates the full AIML pipeline for a single (resume, job) pair:

    Text -> Preprocessing -> NLP -> Feature Extraction -> TF-IDF/Embeddings
         -> Similarity Calculation -> Skill Matching -> Scoring -> Recommendations

...and persists the result. Shared by both places analysis can be triggered
from (the "analyze against this job" shortcut, and the explicit run route).
"""

import json

from app.repositories import (
    get_or_create_skill,
    create_analysis,
    add_analysis_skill,
    add_recommendation,
)
from app.analysis.similarity import semantic_similarity
from app.analysis.skill_match import match_skills, prioritize_missing_skills, keyword_match
from app.analysis.ats import compute_ats_score
from app.analysis.scoring import compute_education_match, compute_experience_match, compute_compatibility_score
from app.analysis.recommendations import (
    generate_improvement_suggestions,
    generate_skill_recommendations,
    build_explainability,
)


def get_weights_from_config(config):
    return {
        "skill": config["WEIGHT_SKILL_MATCH"],
        "keyword": config["WEIGHT_KEYWORD_MATCH"],
        "semantic": config["WEIGHT_SEMANTIC_SIMILARITY"],
        "education": config["WEIGHT_EDUCATION_MATCH"],
        "experience": config["WEIGHT_EXPERIENCE_MATCH"],
    }


def run_full_analysis(resume_row, job_row, weights, use_transformer=False):
    resume_parsed = json.loads(resume_row["parsed_data"]) if resume_row.get("parsed_data") else {}
    job_parsed = json.loads(job_row["parsed_data"]) if job_row.get("parsed_data") else {}
    resume_text = resume_row.get("extracted_text") or ""
    job_text = job_row.get("description") or ""

    skill_result = match_skills(
        resume_parsed.get("skills", []),
        job_parsed.get("required_skills", []),
        job_parsed.get("preferred_skills", []),
    )
    keyword_result = keyword_match(resume_text, job_parsed.get("keywords", []))
    semantic_score, _semantic_method = semantic_similarity(resume_text, job_text, use_transformer=use_transformer)
    education_score = compute_education_match(resume_parsed.get("education_level", 0), job_parsed.get("education_level", 0))
    experience_score = compute_experience_match(resume_parsed.get("experience_years"), job_parsed.get("experience_years_required"))

    compatibility_score = compute_compatibility_score(
        skill_result["skill_match_score"],
        keyword_result["keyword_match_score"],
        semantic_score,
        education_score,
        experience_score,
        weights,
    )
    ats_result = compute_ats_score(resume_parsed, resume_text, job_parsed.get("keywords", []))
    priorities = prioritize_missing_skills(skill_result["missing"], job_text)
    explainability = build_explainability(skill_result, education_score >= 60, semantic_score)

    analysis_id = create_analysis({
        "resume_id": resume_row["resume_id"],
        "job_id": job_row["job_id"],
        "compatibility_score": compatibility_score,
        "ats_score": ats_result["ats_score"],
        "skill_match_score": skill_result["skill_match_score"],
        "keyword_match_score": keyword_result["keyword_match_score"],
        "semantic_score": semantic_score,
        "education_match_score": education_score,
        "experience_match_score": experience_score,
        "ats_details": ats_result["checks"],
        "explainability": explainability,
    })

    for name in skill_result["matching"]:
        skill_id = get_or_create_skill(name)
        add_analysis_skill(analysis_id, skill_id, "matching", None)
    for name in skill_result["missing"]:
        skill_id = get_or_create_skill(name)
        add_analysis_skill(analysis_id, skill_id, "missing", priorities.get(name, "Medium"))
    for name in skill_result["additional"]:
        skill_id = get_or_create_skill(name)
        add_analysis_skill(analysis_id, skill_id, "additional", None)

    for suggestion in generate_improvement_suggestions(resume_parsed, ats_result, skill_result):
        add_recommendation(analysis_id, "improvement", suggestion["text"], suggestion["priority"])
    for rec in generate_skill_recommendations(priorities):
        add_recommendation(analysis_id, "skill", rec["skill"], rec["priority"])

    return analysis_id
