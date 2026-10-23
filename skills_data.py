"""
Skill dictionary / taxonomy used across the app for skill extraction and
matching. This acts as the "skills database" described in the project spec.
Keep each skill in exactly one category to avoid duplicate primary keys when
seeding the `skills` table.
"""

SKILL_TAXONOMY = {
    "Programming Languages": [
        "Python", "Java", "JavaScript", "TypeScript", "C++", "C", "C#", "Go", "Rust",
        "Ruby", "PHP", "Swift", "Kotlin", "R", "MATLAB", "Scala", "Perl", "SQL",
        "HTML", "CSS", "Dart", "Objective-C", "Bash", "Shell Scripting", "VB.NET",
    ],
    "Frameworks & Libraries": [
        "Flask", "Django", "FastAPI", "React", "Angular", "Vue.js", "Node.js",
        "Express.js", "Spring", "Spring Boot", ".NET", "ASP.NET", "Laravel",
        "Ruby on Rails", "Next.js", "jQuery", "Bootstrap", "TensorFlow", "PyTorch",
        "Keras", "Scikit-learn", "Pandas", "NumPy", "OpenCV", "Redux", "GraphQL",
    ],
    "Databases": [
        "MySQL", "PostgreSQL", "MongoDB", "SQLite", "Oracle", "SQL Server", "Redis",
        "Cassandra", "DynamoDB", "Firebase", "MariaDB", "Elasticsearch",
    ],
    "Cloud & DevOps": [
        "AWS", "Azure", "Google Cloud", "Docker", "Kubernetes", "Jenkins", "Git",
        "GitHub", "GitLab", "CI/CD", "Terraform", "Ansible", "Linux", "Nginx",
        "Apache", "Heroku", "DigitalOcean", "CloudFormation", "Chef", "Puppet",
    ],
    "Data Science & AI": [
        "Machine Learning", "Deep Learning", "Natural Language Processing", "Computer Vision",
        "Data Analysis", "Data Visualization", "Tableau", "Power BI", "Excel", "Advanced Excel",
        "Apache Spark", "Hadoop", "Statistics", "A/B Testing", "Feature Engineering",
        "Data Mining", "Big Data", "ETL",
    ],
    "Cybersecurity": [
        "Penetration Testing", "Ethical Hacking", "Network Security", "Cryptography", "SIEM",
        "Firewall Management", "OWASP", "Vulnerability Assessment", "Incident Response",
        "IAM", "Threat Modeling",
    ],
    "Tools & Platforms": [
        "JIRA", "Confluence", "Slack", "VS Code", "Postman", "Figma", "PowerPoint",
        "Trello", "Notion", "Agile", "Scrum", "REST API", "Microservices", "Unit Testing",
        "Object-Oriented Programming",
    ],
}

# Common shorthand / alternate spellings mapped to their canonical skill name.
SKILL_ALIASES = {
    "js": "JavaScript",
    "ts": "TypeScript",
    "ml": "Machine Learning",
    "dl": "Deep Learning",
    "nlp": "Natural Language Processing",
    "cv": "Computer Vision",
    "k8s": "Kubernetes",
    "gcp": "Google Cloud",
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "reactjs": "React",
    "react.js": "React",
    "vuejs": "Vue.js",
    "nodejs": "Node.js",
    "node": "Node.js",
    "expressjs": "Express.js",
    "express": "Express.js",
    "sklearn": "Scikit-learn",
    "scikit learn": "Scikit-learn",
    "restful api": "REST API",
    "rest apis": "REST API",
    "ci/cd": "CI/CD",
    "cicd": "CI/CD",
    "powerbi": "Power BI",
    "amazon web services": "AWS",
    "microsoft azure": "Azure",
    "spring boot": "Spring Boot",
    "oop": "Object-Oriented Programming",
}

ALL_SKILLS = sorted({s for skills in SKILL_TAXONOMY.values() for s in skills})

# Sanity: every alias target must be a real skill in the taxonomy.
_missing = [v for v in SKILL_ALIASES.values() if v not in ALL_SKILLS]
if _missing:  # pragma: no cover
    raise AssertionError(f"SKILL_ALIASES point to unknown skills: {_missing}")
