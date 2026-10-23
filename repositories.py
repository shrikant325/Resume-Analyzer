"""
Repository layer: one small function per query, used by the route modules.
Keeping this separate from db.py keeps the SQL statements co-located with the
domain concept they belong to (users, resumes, jobs, analyses...).
"""

import json
from datetime import datetime

from app.db import execute, query_one, query_all


def _now():
    return datetime.utcnow().isoformat(sep=" ", timespec="seconds")


# --------------------------------------------------------------------------
# Users
# --------------------------------------------------------------------------

def create_user(name, email, password_hash):
    return execute(
        "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
        (name, email, password_hash, _now()),
    )


def get_user_by_email(email):
    return query_one("SELECT * FROM users WHERE email = ?", (email,))


def get_user_by_id(user_id):
    return query_one("SELECT * FROM users WHERE user_id = ?", (user_id,))


def update_user_name(user_id, name):
    execute("UPDATE users SET name = ? WHERE user_id = ?", (name, user_id))


def update_user_password(user_id, password_hash):
    execute("UPDATE users SET password_hash = ? WHERE user_id = ?", (password_hash, user_id))


# --------------------------------------------------------------------------
# Resumes
# --------------------------------------------------------------------------

def create_resume(user_id, file_name, file_path, extracted_text, parsed_data):
    return execute(
        """INSERT INTO resumes (user_id, file_name, file_path, extracted_text, parsed_data, upload_date)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (user_id, file_name, file_path, extracted_text, json.dumps(parsed_data), _now()),
    )


def get_resume(resume_id):
    return query_one("SELECT * FROM resumes WHERE resume_id = ?", (resume_id,))


def get_resumes_for_user(user_id):
    return query_all("SELECT * FROM resumes WHERE user_id = ? ORDER BY upload_date DESC", (user_id,))


def delete_resume(resume_id):
    execute("DELETE FROM resumes WHERE resume_id = ?", (resume_id,))


# --------------------------------------------------------------------------
# Job descriptions
# --------------------------------------------------------------------------

def create_job(user_id, job_title, company, description, parsed_data):
    return execute(
        """INSERT INTO job_descriptions (user_id, job_title, company, description, parsed_data, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (user_id, job_title, company, description, json.dumps(parsed_data), _now()),
    )


def get_job(job_id):
    return query_one("SELECT * FROM job_descriptions WHERE job_id = ?", (job_id,))


def get_jobs_for_user(user_id):
    return query_all(
        "SELECT * FROM job_descriptions WHERE user_id = ? ORDER BY created_at DESC", (user_id,)
    )


# --------------------------------------------------------------------------
# Skills
# --------------------------------------------------------------------------

def get_or_create_skill(skill_name, skill_category="Other"):
    row = query_one("SELECT * FROM skills WHERE skill_name = ?", (skill_name,))
    if row:
        return row["skill_id"]
    return execute(
        "INSERT INTO skills (skill_name, skill_category) VALUES (?, ?)", (skill_name, skill_category)
    )


# --------------------------------------------------------------------------
# Analyses
# --------------------------------------------------------------------------

def create_analysis(data):
    return execute(
        """INSERT INTO analyses (
               resume_id, job_id, compatibility_score, ats_score, skill_match_score,
               keyword_match_score, semantic_score, education_match_score, experience_match_score,
               ats_details, explainability, analysis_date
           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            data["resume_id"],
            data["job_id"],
            data["compatibility_score"],
            data["ats_score"],
            data["skill_match_score"],
            data["keyword_match_score"],
            data["semantic_score"],
            data["education_match_score"],
            data["experience_match_score"],
            json.dumps(data["ats_details"]),
            json.dumps(data["explainability"]),
            _now(),
        ),
    )


def get_analysis(analysis_id):
    return query_one(
        """SELECT a.*, r.file_name AS resume_file_name, r.user_id AS resume_user_id,
                  j.job_title, j.company, j.description AS job_description
           FROM analyses a
           JOIN resumes r ON a.resume_id = r.resume_id
           JOIN job_descriptions j ON a.job_id = j.job_id
           WHERE a.analysis_id = ?""",
        (analysis_id,),
    )


def get_analyses_for_user(user_id, limit=None):
    q = """SELECT a.*, r.file_name AS resume_file_name, j.job_title, j.company
           FROM analyses a
           JOIN resumes r ON a.resume_id = r.resume_id
           JOIN job_descriptions j ON a.job_id = j.job_id
           WHERE r.user_id = ?
           ORDER BY a.analysis_date DESC"""
    if limit:
        q += " LIMIT " + str(int(limit))
    return query_all(q, (user_id,))


def add_analysis_skill(analysis_id, skill_id, status, priority=None):
    execute(
        "INSERT INTO analysis_skills (analysis_id, skill_id, skill_status, priority) VALUES (?, ?, ?, ?)",
        (analysis_id, skill_id, status, priority),
    )


def get_analysis_skills(analysis_id):
    return query_all(
        """SELECT s.skill_name, ansk.skill_status, ansk.priority
           FROM analysis_skills ansk
           JOIN skills s ON ansk.skill_id = s.skill_id
           WHERE ansk.analysis_id = ?""",
        (analysis_id,),
    )


def add_recommendation(analysis_id, rec_type, text, priority):
    execute(
        """INSERT INTO recommendations (analysis_id, recommendation_type, recommendation_text, priority)
           VALUES (?, ?, ?, ?)""",
        (analysis_id, rec_type, text, priority),
    )


def get_recommendations(analysis_id):
    return query_all("SELECT * FROM recommendations WHERE analysis_id = ?", (analysis_id,))
