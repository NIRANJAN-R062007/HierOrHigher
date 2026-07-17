"""Canonical skill dictionary shared by data generation and feature extraction.

This is *public* domain knowledge (what skills exist, what their aliases are)
— it is deliberately separate from the generator's hidden scoring rubric,
which must never be importable by training or inference code.
"""

# -- canonical skills per domain ------------------------------------------

DOMAIN_SKILLS: dict[str, list[str]] = {
    "software": [
        "Python", "JavaScript", "TypeScript", "Java", "C++", "Go", "React",
        "Node.js", "Django", "FastAPI", "SQL", "PostgreSQL", "MongoDB",
        "Redis", "Docker", "Kubernetes", "AWS", "Google Cloud", "Azure",
        "Git", "CI/CD", "REST APIs", "GraphQL", "Linux", "Microservices",
    ],
    "data": [
        "Python", "SQL", "Pandas", "NumPy", "Scikit-learn", "TensorFlow",
        "PyTorch", "Machine Learning", "Deep Learning", "NLP",
        "Computer Vision", "Data Visualization", "Tableau", "Power BI",
        "Spark", "Airflow", "dbt", "Statistics", "A/B Testing", "ETL",
        "Snowflake", "BigQuery", "Data Modeling",
    ],
    "design": [
        "Figma", "Sketch", "Adobe Photoshop", "Adobe Illustrator",
        "Adobe XD", "Wireframing", "Prototyping", "User Research",
        "Usability Testing", "Design Systems", "Typography",
        "Interaction Design", "Accessibility", "HTML", "CSS",
        "Motion Design", "Branding", "Information Architecture",
    ],
    "marketing": [
        "SEO", "SEM", "Google Analytics", "Google Ads", "Facebook Ads",
        "Content Marketing", "Email Marketing", "Copywriting",
        "Social Media Marketing", "Marketing Automation", "HubSpot",
        "Salesforce", "CRM", "Brand Management", "Market Research", "PPC",
        "Conversion Rate Optimization", "Influencer Marketing",
    ],
    "finance": [
        "Financial Modeling", "Excel", "Valuation", "Accounting", "GAAP",
        "Financial Reporting", "Budgeting", "Forecasting", "Risk Management",
        "Bloomberg Terminal", "SAP", "QuickBooks", "Auditing", "Taxation",
        "Equity Research", "Portfolio Management", "Derivatives", "VBA",
    ],
    "mechanical": [
        "AutoCAD", "SolidWorks", "CATIA", "ANSYS", "MATLAB",
        "Finite Element Analysis", "CFD", "GD&T", "CNC Machining",
        "3D Printing", "Thermodynamics", "HVAC", "Six Sigma",
        "Lean Manufacturing", "PLC Programming", "Robotics",
        "Product Design", "Quality Control",
    ],
}

ALL_SKILLS: list[str] = sorted({s for pool in DOMAIN_SKILLS.values() for s in pool})

# -- alias resolution (lowercased alias -> canonical name) -----------------

SKILL_ALIASES: dict[str, str] = {
    "js": "JavaScript",
    "ts": "TypeScript",
    "gcp": "Google Cloud",
    "google cloud platform": "Google Cloud",
    "amazon web services": "AWS",
    "k8s": "Kubernetes",
    "postgres": "PostgreSQL",
    "mongo": "MongoDB",
    "node": "Node.js",
    "nodejs": "Node.js",
    "reactjs": "React",
    "ml": "Machine Learning",
    "dl": "Deep Learning",
    "natural language processing": "NLP",
    "cv": "Computer Vision",
    "sklearn": "Scikit-learn",
    "scikit learn": "Scikit-learn",
    "tf": "TensorFlow",
    "photoshop": "Adobe Photoshop",
    "illustrator": "Adobe Illustrator",
    "xd": "Adobe XD",
    "ux research": "User Research",
    "ia": "Information Architecture",
    "search engine optimization": "SEO",
    "search engine marketing": "SEM",
    "ga": "Google Analytics",
    "cro": "Conversion Rate Optimization",
    "adwords": "Google Ads",
    "fb ads": "Facebook Ads",
    "fea": "Finite Element Analysis",
    "computational fluid dynamics": "CFD",
    "cad": "AutoCAD",
    "solid works": "SolidWorks",
    "dcf": "Valuation",
    "fp&a": "Budgeting",
    "restful apis": "REST APIs",
    "rest": "REST APIs",
    "ci cd": "CI/CD",
    "cicd": "CI/CD",
    "continuous integration": "CI/CD",
}

# -- education ladder (spec: 0=none ... 4=PhD) -----------------------------

EDUCATION_LEVELS: dict[int, str] = {
    0: "none",
    1: "high school",
    2: "bachelor",
    3: "master",
    4: "phd",
}

# Keyword -> level, checked in order (most specific first).
EDUCATION_KEYWORDS: list[tuple[str, int]] = [
    ("ph.d", 4), ("phd", 4), ("doctorate", 4),
    ("master", 3), ("m.s.", 3), ("msc", 3), ("mba", 3), ("m.tech", 3),
    ("bachelor", 2), ("b.s.", 2), ("bsc", 2), ("b.tech", 2), ("b.e.", 2),
    ("b.a.", 2), ("undergraduate degree", 2),
    ("high school", 1), ("diploma", 1),
]

# -- resume sections the completeness feature looks for --------------------

EXPECTED_SECTIONS: list[str] = ["summary", "skills", "experience", "education", "projects"]
