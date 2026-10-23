"""
Application configuration.

By default the app runs on SQLite (Python's built-in `sqlite3` module) so it
works immediately with zero external services. Set DB_BACKEND=mysql (and the
MYSQL_* variables) to use MySQL instead, exactly as requested in the project
spec — see the README for the two-step switch-over.
"""

import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
instance_dir = os.path.join(basedir, "instance")
uploads_dir = os.path.join(basedir, "uploads")


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-this-in-production")

    # ---- Database ----
    DB_BACKEND = os.environ.get("DB_BACKEND", "sqlite")  # "sqlite" or "mysql"
    SQLITE_PATH = os.environ.get("SQLITE_PATH", os.path.join(instance_dir, "resume_analyzer.db"))

    MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
    MYSQL_PORT = int(os.environ.get("MYSQL_PORT", "3306"))
    MYSQL_USER = os.environ.get("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "")
    MYSQL_DB = os.environ.get("MYSQL_DB", "resume_analyzer")

    # ---- Uploads ----
    UPLOAD_FOLDER = uploads_dir
    ALLOWED_EXTENSIONS = {"pdf", "docx"}
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8 MB

    # ---- Sessions ----
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)

    # ---- Optional enhanced NLP ----
    # Off by default so the app never tries to download a model at runtime.
    # Install `sentence-transformers` and set this to "true" to opt in.
    USE_SENTENCE_TRANSFORMERS = os.environ.get("USE_SENTENCE_TRANSFORMERS", "false").lower() == "true"

    # ---- Compatibility score weights (must sum to 1.0) ----
    WEIGHT_SKILL_MATCH = 0.40
    WEIGHT_KEYWORD_MATCH = 0.20
    WEIGHT_SEMANTIC_SIMILARITY = 0.20
    WEIGHT_EDUCATION_MATCH = 0.10
    WEIGHT_EXPERIENCE_MATCH = 0.10


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
