"""
Lightweight database access layer.

Rather than pulling in an ORM, this module talks to the database with plain,
parameterized SQL (never string-formatted values -> no SQL injection) through
a tiny abstraction that supports two backends:

  * sqlite  (default) -> Python's built-in `sqlite3` module, zero setup.
  * mysql             -> PyMySQL (`pip install pymysql`), matching the
                          project spec's requirement to use MySQL.

Both backends share the same table design described in the spec (users,
resumes, job_descriptions, analyses, skills, analysis_skills,
recommendations), with a couple of extra JSON columns added to store rich
parsed/explainability data used by the dashboard.
"""

import sqlite3
from flask import g, current_app


# --------------------------------------------------------------------------
# Connection handling
# --------------------------------------------------------------------------

def get_db():
    """Return a request-scoped database connection, creating it if needed."""
    if "db" not in g:
        backend = current_app.config["DB_BACKEND"]
        if backend == "mysql":
            try:
                import pymysql
                import pymysql.cursors
            except ImportError as exc:  # pragma: no cover - environment dependent
                raise RuntimeError(
                    "DB_BACKEND is set to 'mysql' but PyMySQL is not installed. "
                    "Run `pip install pymysql` or switch DB_BACKEND back to 'sqlite'."
                ) from exc
            g.db = pymysql.connect(
                host=current_app.config["MYSQL_HOST"],
                port=current_app.config["MYSQL_PORT"],
                user=current_app.config["MYSQL_USER"],
                password=current_app.config["MYSQL_PASSWORD"],
                database=current_app.config["MYSQL_DB"],
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=False,
            )
        else:
            conn = sqlite3.connect(current_app.config["SQLITE_PATH"])
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            g.db = conn
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_app(app):
    app.teardown_appcontext(close_db)


def _adapt(query):
    """Translate the `?` placeholder style used everywhere in this codebase
    into `%s` for PyMySQL, which does not understand `?`."""
    if current_app.config["DB_BACKEND"] == "mysql":
        return query.replace("?", "%s")
    return query


# --------------------------------------------------------------------------
# Query helpers — every caller in the app goes through these three functions
# --------------------------------------------------------------------------

def execute(query, params=(), commit=True):
    """Run an INSERT/UPDATE/DELETE. Returns the new row id for INSERTs."""
    db = get_db()
    cur = db.cursor()
    cur.execute(_adapt(query), params)
    if commit:
        db.commit()
    last_id = cur.lastrowid
    cur.close()
    return last_id


def query_one(query, params=()):
    db = get_db()
    cur = db.cursor()
    cur.execute(_adapt(query), params)
    row = cur.fetchone()
    cur.close()
    return dict(row) if row is not None else None


def query_all(query, params=()):
    db = get_db()
    cur = db.cursor()
    cur.execute(_adapt(query), params)
    rows = cur.fetchall()
    cur.close()
    return [dict(r) for r in rows]


# --------------------------------------------------------------------------
# Schema
# --------------------------------------------------------------------------

SCHEMA_SQLITE = [
    """CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(120) NOT NULL,
        email VARCHAR(160) NOT NULL UNIQUE,
        password_hash VARCHAR(255) NOT NULL,
        created_at DATETIME
    );""",
    """CREATE TABLE IF NOT EXISTS resumes (
        resume_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        file_name VARCHAR(255) NOT NULL,
        file_path VARCHAR(500) NOT NULL,
        extracted_text TEXT,
        parsed_data TEXT,
        upload_date DATETIME,
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
    );""",
    """CREATE TABLE IF NOT EXISTS job_descriptions (
        job_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        job_title VARCHAR(200) NOT NULL,
        company VARCHAR(200),
        description TEXT NOT NULL,
        parsed_data TEXT,
        created_at DATETIME,
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
    );""",
    """CREATE TABLE IF NOT EXISTS analyses (
        analysis_id INTEGER PRIMARY KEY AUTOINCREMENT,
        resume_id INTEGER NOT NULL,
        job_id INTEGER NOT NULL,
        compatibility_score REAL DEFAULT 0,
        ats_score REAL DEFAULT 0,
        skill_match_score REAL DEFAULT 0,
        keyword_match_score REAL DEFAULT 0,
        semantic_score REAL DEFAULT 0,
        education_match_score REAL DEFAULT 0,
        experience_match_score REAL DEFAULT 0,
        ats_details TEXT,
        explainability TEXT,
        analysis_date DATETIME,
        FOREIGN KEY (resume_id) REFERENCES resumes(resume_id) ON DELETE CASCADE,
        FOREIGN KEY (job_id) REFERENCES job_descriptions(job_id) ON DELETE CASCADE
    );""",
    """CREATE TABLE IF NOT EXISTS skills (
        skill_id INTEGER PRIMARY KEY AUTOINCREMENT,
        skill_name VARCHAR(120) NOT NULL UNIQUE,
        skill_category VARCHAR(80)
    );""",
    """CREATE TABLE IF NOT EXISTS analysis_skills (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        analysis_id INTEGER NOT NULL,
        skill_id INTEGER NOT NULL,
        skill_status VARCHAR(20),
        priority VARCHAR(10),
        FOREIGN KEY (analysis_id) REFERENCES analyses(analysis_id) ON DELETE CASCADE,
        FOREIGN KEY (skill_id) REFERENCES skills(skill_id) ON DELETE CASCADE
    );""",
    """CREATE TABLE IF NOT EXISTS recommendations (
        recommendation_id INTEGER PRIMARY KEY AUTOINCREMENT,
        analysis_id INTEGER NOT NULL,
        recommendation_type VARCHAR(30),
        recommendation_text TEXT,
        priority VARCHAR(10),
        FOREIGN KEY (analysis_id) REFERENCES analyses(analysis_id) ON DELETE CASCADE
    );""",
]

SCHEMA_MYSQL = [
    """CREATE TABLE IF NOT EXISTS users (
        user_id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(120) NOT NULL,
        email VARCHAR(160) NOT NULL UNIQUE,
        password_hash VARCHAR(255) NOT NULL,
        created_at DATETIME
    ) ENGINE=InnoDB;""",
    """CREATE TABLE IF NOT EXISTS resumes (
        resume_id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        file_name VARCHAR(255) NOT NULL,
        file_path VARCHAR(500) NOT NULL,
        extracted_text LONGTEXT,
        parsed_data LONGTEXT,
        upload_date DATETIME,
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
    ) ENGINE=InnoDB;""",
    """CREATE TABLE IF NOT EXISTS job_descriptions (
        job_id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        job_title VARCHAR(200) NOT NULL,
        company VARCHAR(200),
        description LONGTEXT NOT NULL,
        parsed_data LONGTEXT,
        created_at DATETIME,
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
    ) ENGINE=InnoDB;""",
    """CREATE TABLE IF NOT EXISTS analyses (
        analysis_id INT AUTO_INCREMENT PRIMARY KEY,
        resume_id INT NOT NULL,
        job_id INT NOT NULL,
        compatibility_score FLOAT DEFAULT 0,
        ats_score FLOAT DEFAULT 0,
        skill_match_score FLOAT DEFAULT 0,
        keyword_match_score FLOAT DEFAULT 0,
        semantic_score FLOAT DEFAULT 0,
        education_match_score FLOAT DEFAULT 0,
        experience_match_score FLOAT DEFAULT 0,
        ats_details LONGTEXT,
        explainability LONGTEXT,
        analysis_date DATETIME,
        FOREIGN KEY (resume_id) REFERENCES resumes(resume_id) ON DELETE CASCADE,
        FOREIGN KEY (job_id) REFERENCES job_descriptions(job_id) ON DELETE CASCADE
    ) ENGINE=InnoDB;""",
    """CREATE TABLE IF NOT EXISTS skills (
        skill_id INT AUTO_INCREMENT PRIMARY KEY,
        skill_name VARCHAR(120) NOT NULL UNIQUE,
        skill_category VARCHAR(80)
    ) ENGINE=InnoDB;""",
    """CREATE TABLE IF NOT EXISTS analysis_skills (
        id INT AUTO_INCREMENT PRIMARY KEY,
        analysis_id INT NOT NULL,
        skill_id INT NOT NULL,
        skill_status VARCHAR(20),
        priority VARCHAR(10),
        FOREIGN KEY (analysis_id) REFERENCES analyses(analysis_id) ON DELETE CASCADE,
        FOREIGN KEY (skill_id) REFERENCES skills(skill_id) ON DELETE CASCADE
    ) ENGINE=InnoDB;""",
    """CREATE TABLE IF NOT EXISTS recommendations (
        recommendation_id INT AUTO_INCREMENT PRIMARY KEY,
        analysis_id INT NOT NULL,
        recommendation_type VARCHAR(30),
        recommendation_text LONGTEXT,
        priority VARCHAR(10),
        FOREIGN KEY (analysis_id) REFERENCES analyses(analysis_id) ON DELETE CASCADE
    ) ENGINE=InnoDB;""",
]


def init_db(app):
    """Create tables (if missing) and seed the skills dictionary."""
    with app.app_context():
        backend = app.config["DB_BACKEND"]
        schema = SCHEMA_MYSQL if backend == "mysql" else SCHEMA_SQLITE
        db = get_db()
        cur = db.cursor()
        for statement in schema:
            cur.execute(statement)
        db.commit()
        cur.close()
        _seed_skills()


def _seed_skills():
    from app.nlp.skills_data import SKILL_TAXONOMY

    existing = query_one("SELECT COUNT(*) AS c FROM skills")
    if existing and existing["c"] > 0:
        return
    for category, skills in SKILL_TAXONOMY.items():
        for skill_name in skills:
            try:
                execute(
                    "INSERT INTO skills (skill_name, skill_category) VALUES (?, ?)",
                    (skill_name, category),
                    commit=False,
                )
            except Exception:
                # Duplicate skill name across categories - safe to skip.
                pass
    get_db().commit()
