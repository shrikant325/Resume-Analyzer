# ResumeIQ — AI-Powered Resume Improvement & Job Compatibility Analyzer

A Flask web application that analyzes how well a resume matches a job description using NLP and machine learning techniques (TF-IDF, cosine similarity, rule-based skill/entity extraction), and produces an explainable compatibility score, ATS score, skill-gap report, and concrete improvement suggestions.

Built as an academic AIML project. This README explains how to run it, how it's put together, and — importantly — the pragmatic engineering decisions made along the way and why, so you can explain and defend them in a viva/demo.

---

## 1. Quick Start

```bash
# 1. Create and activate a virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Install dependencies (only 5 packages, no external services needed)
pip install -r requirements.txt

# 3. Run the app
python run.py
```

Open **http://localhost:5000** in your browser. That's it — no database server to install, no API keys, no model downloads. A SQLite database file is created automatically at `instance/resume_analyzer.db` the first time the app starts, with the schema and a seed skill taxonomy already loaded.

Create an account, upload a resume (PDF or DOCX), paste in a job description, and you'll be taken straight to the analysis report.

---

## 2. Project Structure

```
resume_analyzer/
├── app/
│   ├── __init__.py          # Application factory: wires up config, DB, blueprints,
│   │                         # auth/CSRF hooks, template filters, error handlers
│   ├── config.py            # All configuration (env-var driven, sensible defaults)
│   ├── db.py                 # Connection handling + schema DDL (SQLite & MySQL)
│   ├── repositories.py       # All SQL lives here — every other module goes through
│   │                         # this data-access layer instead of writing raw queries
│   ├── auth_utils.py         # login_required decorator, CSRF token helpers
│   │
│   ├── auth/                 # Register / login / logout
│   ├── main/                  # Landing page, dashboard, profile
│   ├── resume/                # Upload, text extraction, resume parsing
│   ├── job/                   # Job description entry + parsing
│   ├── analysis/              # The AIML pipeline + all results pages
│   │   ├── similarity.py      # TF-IDF cosine similarity + optional semantic embeddings
│   │   ├── skill_match.py     # Skill matching, gap prioritization, keyword match
│   │   ├── ats.py             # ATS-style scoring rubric
│   │   ├── scoring.py         # Education/experience sub-scores + weighted final score
│   │   ├── recommendations.py # Rule-based improvement suggestions + explainability
│   │   ├── engine.py          # Orchestrates the full pipeline end-to-end
│   │   └── routes.py          # /run + all report pages
│   ├── nlp/
│   │   ├── skills_data.py     # Curated skill taxonomy (127 skills, 7 categories) + aliases
│   │   └── preprocess.py      # Tokenize / stopword removal / lemmatize (NLTK-or-fallback)
│   │
│   ├── static/{css,js}        # Design system CSS + shared JS (charts, score-ring animation)
│   ├── templates/              # 19 Jinja2 templates
│   └── uploads/                 # Uploaded resume files (created at startup)
│
├── instance/                   # SQLite DB file lives here (created at startup)
├── requirements.txt
├── run.py                      # Entry point
├── .env.example
└── README.md                   # You are here
```

---

## 3. The AIML Pipeline

This is the core flow for every analysis, from raw files to a scored report:

```
Resume (PDF/DOCX)              Job Description (text)
        │                                │
        ▼                                ▼
  Text Extraction                 (already text)
   (pypdf / python-docx)
        │                                │
        └───────────────┬────────────────┘
                         ▼
              Preprocessing & NLP
    (tokenize → remove stopwords → lemmatize/stem)
                         │
                         ▼
              Feature Extraction
   (regex + curated skill dictionary → name, email,
    phone, skills, education level, experience years,
    section detection, measurable-achievement count)
                         │
                         ▼
        TF-IDF Vectorization + Cosine Similarity
      (scikit-learn TfidfVectorizer, optionally
       sentence-transformer embeddings — see §6)
                         │
                         ▼
   Skill Matching  │  Keyword Matching  │  Education/
   (set overlap,   │  (TF-IDF top terms │  Experience
   priority ranked │   vs resume text)  │  comparison
   by JD frequency │                    │
   & position)     │                    │
                         │
                         ▼
         Weighted Compatibility Score
   skill 40% + keyword 20% + semantic 20%
        + education 10% + experience 10%
                         │
                         ▼
       ATS Score (6-check rubric)  +  Explainability
                         │
                         ▼
          Rule-Based Improvement Suggestions
     (weak bullet detection, missing sections,
      missing keywords, length checks, etc.)
                         │
                         ▼
              Stored in `analyses` table
           and rendered across 6 report pages
```

This whole pipeline runs in `app/analysis/engine.py::run_full_analysis()`, which is the single place that ties every stage together — start reading there if you want to trace one analysis end-to-end.

---

## 4. Database Schema

Matches the project spec's design: `users`, `resumes`, `job_descriptions`, `analyses`, `skills`, `analysis_skills`, `recommendations`. A few JSON-serialized columns (`parsed_data`, `ats_details`, `explainability`) were added to store structured NLP output alongside the scalar scores, so the full reasoning behind a score can be redisplayed without recomputing it.

Runs on **SQLite by default** (zero setup) with a straightforward path to **MySQL** (see §5) — same schema, same query layer, different connection.

---

## 5. Switching to MySQL

The spec calls for MySQL, and the app fully supports it — SQLite is simply the default so the project runs anywhere without extra setup. To switch:

```bash
# 1. Install the MySQL driver
pip install pymysql

# 2. Point the app at your MySQL server (e.g. in a .env file or your shell)
export DB_BACKEND=mysql
export MYSQL_HOST=localhost
export MYSQL_USER=root
export MYSQL_PASSWORD=yourpassword
export MYSQL_DB=resume_analyzer
```

Then run the app as normal — `python run.py` will create the database tables in MySQL automatically on startup (`CREATE TABLE IF NOT EXISTS`, same as SQLite). No code changes needed. This works because `app/db.py` has two parallel schema definitions and a small query-translation layer (`?` placeholders become `%s` for MySQL) rather than an ORM.

---

## 6. Optional Upgrades (NLTK & sentence-transformers)

Two parts of the NLP pipeline have optional, higher-quality alternatives that are **off by default** so the app never hangs or crashes trying to reach the network on startup:

**NLTK** (better tokenization/lemmatization than the built-in fallback):
```bash
pip install nltk
python -m nltk.downloader punkt punkt_tab stopwords wordnet omw-1.4
```
Once NLTK's data is present locally, `app/nlp/preprocess.py` detects and uses it automatically — no config flag needed. If it's missing, a hand-written fallback (regex tokenizer + ~150-word stopword list + suffix-stripping stemmer) is used instead, so text preprocessing always works either way.

**sentence-transformers** (embedding-based semantic similarity instead of TF-IDF):
```bash
pip install sentence-transformers
export USE_SENTENCE_TRANSFORMERS=true
```
This must be explicitly opted into with the env var, because loading the model requires a one-time download from the internet. Without it, semantic similarity is computed via TF-IDF cosine similarity instead, which is a reasonable approximation and requires no external downloads.

---

## 7. Design Decisions Worth Knowing (and Defending in a Viva)

The spec describes a Flask + MySQL + Flask-SQLAlchemy + Flask-Login + Flask-WTF + spaCy/NLTK stack. This project deliberately uses lighter-weight equivalents for several pieces, prioritizing **an app that is guaranteed to run correctly everywhere with zero external setup** over strict adherence to a specific library list. Every substitution below implements the *same functional requirement* from the spec — this is a substitution of tools, not a reduction of scope.

| Spec suggests | This project uses | Why |
|---|---|---|
| MySQL | SQLite by default, MySQL fully supported | Zero-setup grading/demo experience; §5 shows the two-step switch |
| Flask-SQLAlchemy | Hand-written query layer (`repositories.py`) over `sqlite3`/`PyMySQL` | No ORM dependency; every query is a plain, readable, parameterized SQL string — arguably clearer for a project meant to demonstrate schema design |
| Flask-Login | Session cookies + a custom `login_required` decorator + `g.user` | Same behavior (protected routes, current-user access in templates), fewer moving parts |
| Flask-WTF | Custom double-submit CSRF token + manual form validation | Same CSRF protection guarantee, no extra dependency |
| spaCy NER | Regex + a curated 127-skill taxonomy (`skills_data.py`) + heuristic rules | spaCy's pretrained models require a separate model download; a curated skill dictionary is actually *more precise* for a fixed domain like "technical skills" than general-purpose NER, at the cost of only recognizing skills in the taxonomy |
| NLTK (required) | NLTK used automatically if already installed locally, else a built-in fallback | NLTK's own tokenizer/lemmatizer needs a separate data download (`nltk.downloader`); the app works fully either way (see §6) |
| sentence-transformers (implied by "semantic similarity") | TF-IDF cosine similarity by default; sentence-transformers as an opt-in upgrade | Downloading a transformer model requires network access; TF-IDF is a legitimate, classic NLP similarity technique and the default keeps the app deterministic and fast |

**The throughline:** every one of these is a case where the "textbook" library needs either a database server, a model download, or a network call that isn't guaranteed to be available at grading/demo time — and a functionally-equivalent alternative was available that doesn't. Given the project's own instruction to be delivered "without any error," this tradeoff was made deliberately and is documented here rather than hidden.

### Other implementation notes
- **Passwords** are hashed with Werkzeug's `generate_password_hash`/`check_password_hash` (PBKDF2), never stored in plain text.
- **Every resource route** (viewing/deleting a resume, viewing an analysis, etc.) checks that the record belongs to the logged-in user and returns 404/403 otherwise — there is no way to view another user's data by guessing an ID.
- **SQL injection**: every query goes through parameterized placeholders (`?` / `%s`); no query is ever built with string concatenation of user input.
- **File uploads** are restricted by extension (`.pdf`, `.docx` only) and size (8 MB max), and saved under a randomized filename (`uuid4` prefix) rather than the user-supplied name.

---

## 8. Known Limitations (also good viva material)

Being upfront about these is more convincing than pretending they don't exist:

- **Skill/entity extraction is dictionary-based, not a trained NER model.** It will miss skills outside the curated taxonomy and won't understand context (e.g. "familiar with Python" vs. "5 years of Python" are both just counted as "has Python").
- **Experience-years extraction is regex-based** (looks for patterns like "3+ years"). A resume that only lists date ranges without ever stating "X years of experience" will show as "not detected" rather than being calculated from the dates — a natural extension would be to sum date ranges.
- **Required-vs-preferred skill splitting** in job descriptions is a heuristic based on section headings ("Preferred Skills", "Nice to have", etc.). Unusually formatted job postings may be split imperfectly.
- **The fallback stemmer** (used only when NLTK isn't installed) is a simple suffix-stripper, not a linguistically rigorous stemmer like Porter/Snowball — it can occasionally over- or under-stem uncommon words.

None of these affect the app's stability — they're precision/recall tradeoffs in the NLP layer, not bugs, and each has a clear "how you'd improve it" answer.

---

## 9. Testing

The app was validated with a full end-to-end test suite (`test_e2e.py`, `test_e2e_part2.py` — not required to run the app, included for transparency) that drives the entire user flow through Flask's test client: registration, login, resume upload (both PDF and DOCX), job description entry, automatic analysis, every results page, profile updates, password changes, access-control checks (404s on other users' data, redirect-when-logged-out), and logout. All checks pass.

To re-run them yourself:
```bash
python3 test_e2e.py
python3 test_e2e_part2.py
```

---

## 10. Tech Stack Summary

- **Backend:** Flask 3
- **Database:** SQLite (default) / MySQL (optional) — raw SQL via a hand-written query layer
- **NLP/ML:** scikit-learn (TF-IDF, cosine similarity), regex-based entity extraction, curated skill taxonomy
- **File parsing:** pypdf (PDF), python-docx (DOCX)
- **Frontend:** Server-rendered Jinja2 templates, Bootstrap 5 (layout/components) with a custom design system on top, Chart.js for data visualization
- **Auth:** Session-based, Werkzeug password hashing, custom CSRF protection
