"""Stage 1 — synthetic resume/JD pair generator.

Produces 30,000 labelled pairs across 6 domains with realistic noise (skill
typos, aliases, dropped sections, inconsistent date formats).

ANTI-LEAKAGE: the scoring rubric below (`_RUBRIC_WEIGHTS`, `_rubric_score`,
and every latent variable) is private to this script. The dataset CSV stores
raw text + score only; training and inference recompute features from text
and MUST NOT import this module.

Run:  python -m ml.generate_data
"""

import random

import numpy as np
import pandas as pd

from ml.common import (
    DATA_DIR,
    DATASET_PATH,
    REFERENCE_MONTH,
    REFERENCE_YEAR,
    SEED,
    score_to_label,
)
from ml.skills import DOMAIN_SKILLS, SKILL_ALIASES

rng = random.Random(SEED)
np_rng = np.random.default_rng(SEED)

# -- world knowledge (titles, companies, adjacency) ------------------------

TITLES = {
    "software": {
        "junior": ["Junior Software Engineer", "Software Developer"],
        "mid": ["Software Engineer", "Backend Developer", "Full Stack Developer"],
        "senior": ["Senior Software Engineer", "Senior Backend Engineer"],
        "lead": ["Staff Software Engineer", "Engineering Lead"],
    },
    "data": {
        "junior": ["Data Analyst", "Junior Data Scientist"],
        "mid": ["Data Scientist", "Data Engineer", "Machine Learning Engineer"],
        "senior": ["Senior Data Scientist", "Senior Machine Learning Engineer"],
        "lead": ["Lead Data Scientist", "Principal Data Engineer"],
    },
    "design": {
        "junior": ["Junior UX Designer", "Design Intern"],
        "mid": ["UX Designer", "Product Designer", "UI Designer"],
        "senior": ["Senior Product Designer", "Senior UX Designer"],
        "lead": ["Design Lead", "Head of Design"],
    },
    "marketing": {
        "junior": ["Marketing Associate", "Marketing Coordinator"],
        "mid": ["Digital Marketing Specialist", "Content Marketing Manager", "SEO Specialist"],
        "senior": ["Senior Marketing Manager", "Growth Marketing Manager"],
        "lead": ["Head of Growth", "Marketing Director"],
    },
    "finance": {
        "junior": ["Junior Financial Analyst", "Accounting Associate"],
        "mid": ["Financial Analyst", "Investment Analyst"],
        "senior": ["Senior Financial Analyst", "Finance Manager"],
        "lead": ["Director of Finance", "Head of FP&A"],
    },
    "mechanical": {
        "junior": ["Junior Mechanical Engineer", "Mechanical Design Trainee"],
        "mid": ["Mechanical Engineer", "Design Engineer", "Manufacturing Engineer"],
        "senior": ["Senior Mechanical Engineer", "Senior Design Engineer"],
        "lead": ["Principal Mechanical Engineer", "Engineering Manager"],
    },
}

SENIORITY_YEARS = {"junior": (0, 2), "mid": (2, 5), "senior": (5, 9), "lead": (8, 13)}

ADJACENT = {
    "software": ["data"],
    "data": ["software", "finance"],
    "design": ["marketing"],
    "marketing": ["design"],
    "finance": ["data"],
    "mechanical": ["software"],
}

FIRST_NAMES = ["Asha", "Rohan", "Priya", "Arjun", "Meera", "Karthik", "Divya",
               "Vikram", "Sneha", "Aditya", "Lakshmi", "Rahul", "Ananya", "Suresh"]
LAST_NAMES = ["Venkat", "Mehta", "Iyer", "Sharma", "Nair", "Reddy", "Patel",
              "Krishnan", "Gupta", "Rao", "Menon", "Das"]
COMPANIES = ["CloudCore", "Metricly", "BrightApps", "NovaWorks", "PixelForge",
             "FinEdge", "TorqueLabs", "GrowthHive", "DataSpring", "BlueLedger"]
SCHOOLS = ["Anna University", "VIT Vellore", "IIT Madras", "NIT Trichy",
           "SRM University", "BITS Pilani", "Delhi University"]

DEGREE_TEXT = {
    1: ["High School Diploma"],
    2: ["B.Tech in {field}", "Bachelor of Science in {field}", "B.E. in {field}"],
    3: ["M.S. in {field}", "Master of Science in {field}", "MBA"],
    4: ["Ph.D. in {field}", "PhD in {field}"],
}
FIELDS = {
    "software": "Computer Science", "data": "Data Science", "design": "Design",
    "marketing": "Marketing", "finance": "Finance", "mechanical": "Mechanical Engineering",
}

# Reverse alias map so resumes sometimes write "GCP" instead of "Google Cloud".
_CANON_TO_ALIASES: dict[str, list[str]] = {}
for alias, canon in SKILL_ALIASES.items():
    _CANON_TO_ALIASES.setdefault(canon, []).append(alias)

# -- HIDDEN RUBRIC (never leaves this file) --------------------------------

_RUBRIC_WEIGHTS = {
    "skill": 0.28, "exp": 0.22, "edu": 0.12,
    "title": 0.16, "kw": 0.12, "sections": 0.10,
}
_NOISE_SIGMA = 4.0


def _rubric_exp_fit(delta_years: float) -> float:
    slope = 0.85 if delta_years < 0 else 0.22
    return 1.0 / (1.0 + np.exp(-(1.4 + slope * delta_years)))


def _rubric_score(lat: dict) -> float:
    """Hidden ground-truth rubric on *latent* (pre-noise) attributes."""
    kw = 0.7 * lat["skill_cov"] + 0.3 * lat["title_rel"]
    raw = (
        _RUBRIC_WEIGHTS["skill"] * lat["skill_cov"]
        + _RUBRIC_WEIGHTS["exp"] * _rubric_exp_fit(lat["cand_years"] - lat["req_years"])
        + _RUBRIC_WEIGHTS["edu"] * lat["edu_fit"]
        + _RUBRIC_WEIGHTS["title"] * lat["title_rel"]
        + _RUBRIC_WEIGHTS["kw"] * kw
        + _RUBRIC_WEIGHTS["sections"] * lat["section_frac"]
    )
    # Stretch below the natural floor (~0.15 even for terrible matches, since
    # sigmoid/education terms never reach 0) so Weak pairs land under 40.
    scaled = 100.0 * (raw - 0.15) / 0.85
    return float(np.clip(scaled + np_rng.normal(0.0, _NOISE_SIGMA), 0.0, 100.0))


# -- text noise helpers ----------------------------------------------------

def _typo(word: str) -> str:
    """Swap two adjacent inner characters, e.g. 'Python' -> 'Pyhton'."""
    if len(word) < 4:
        return word
    i = rng.randrange(1, len(word) - 2)
    return word[:i] + word[i + 1] + word[i] + word[i + 2:]


def _render_skill(skill: str) -> str:
    roll = rng.random()
    if roll < 0.20 and skill in _CANON_TO_ALIASES:
        return rng.choice(_CANON_TO_ALIASES[skill]).upper() if rng.random() < 0.5 \
            else rng.choice(_CANON_TO_ALIASES[skill])
    if roll < 0.28:
        return _typo(skill)
    return skill


def _date_range(end_y: int, end_m: int, months: int, latest: bool) -> str:
    start_m = end_m - months
    start_y = end_y + (start_m - 1) // 12
    start_m = (start_m - 1) % 12 + 1
    style = rng.choice(["month", "slash", "year"])
    sep = rng.choice([" - ", " – ", " to "])
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    if style == "month":
        start = f"{month_names[start_m - 1]} {start_y}"
        end = "Present" if latest else f"{month_names[end_m - 1]} {end_y}"
    elif style == "slash":
        start = f"{start_m:02d}/{start_y}"
        end = "Present" if latest else f"{end_m:02d}/{end_y}"
    else:
        start = str(start_y)
        end = "Present" if latest else str(end_y)
    return f"{start}{sep}{end}"


# -- pair construction -----------------------------------------------------

def _make_jd(domain: str, seniority: str) -> dict:
    title = rng.choice(TITLES[domain][seniority])
    lo, hi = SENIORITY_YEARS[seniority]
    req_years = rng.randint(lo, hi)
    req_edu = rng.choices([0, 2, 3, 4], weights=[10, 55, 30, 5])[0]
    n_skills = rng.randint(6, 12)
    req_skills = rng.sample(DOMAIN_SKILLS[domain], min(n_skills, len(DOMAIN_SKILLS[domain])))
    company = rng.choice(COMPANIES)

    edu_line = {
        0: "", 2: "- Bachelor's degree in a relevant field required\n",
        3: "- Master's degree required\n", 4: "- PhD in a relevant field required\n",
    }[req_edu]
    text = (
        f"Job Title: {title}\n"
        f"Company: {company}\n\n"
        f"About the Role:\n"
        f"We are hiring a {title} to strengthen our {domain} team at {company}. "
        f"You will ship high-impact work with modern tools.\n\n"
        f"Requirements:\n"
        f"- {req_years}+ years of relevant experience\n"
        f"- Proficiency in: {', '.join(req_skills)}\n"
        f"{edu_line}\n"
        f"Responsibilities:\n"
        f"- Own and deliver {domain} initiatives using {req_skills[0]} and {req_skills[1]}\n"
        f"- Collaborate with cross-functional partners and mentor peers\n"
    )
    return {"title": title, "domain": domain, "seniority": seniority,
            "req_years": req_years, "req_edu": req_edu,
            "req_skills": req_skills, "text": text}


def _pick_resume_setup(jd: dict, tier: str) -> dict:
    domain, seniority = jd["domain"], jd["seniority"]
    seniorities = list(SENIORITY_YEARS)
    if tier == "strong":
        r_domain = domain
        coverage = rng.uniform(0.72, 1.0)
        cand_years = jd["req_years"] + (rng.uniform(0, 5) if rng.random() < 0.85
                                        else -rng.uniform(0, 1.5))
        edu = jd["req_edu"] if rng.random() < 0.35 else \
            rng.choices([2, 3, 4], weights=[40, 45, 15])[0]
        if rng.random() < 0.10:
            edu = max(0, jd["req_edu"] - 1)
        r_seniority = seniority if rng.random() < 0.75 else \
            rng.choice(seniorities)
        drop_p = {"summary": 0.08, "projects": 0.12, "skills": 0.02,
                  "experience": 0.0, "education": 0.03}
    elif tier == "moderate":
        r_domain = domain if rng.random() < 0.60 else rng.choice(ADJACENT[domain])
        coverage = rng.uniform(0.35, 0.68)
        cand_years = max(0.0, jd["req_years"] + rng.uniform(-3.5, 2.0))
        edu = rng.choices([1, 2, 3, 4], weights=[10, 50, 32, 8])[0]
        r_seniority = rng.choice(seniorities)
        drop_p = {"summary": 0.20, "projects": 0.25, "skills": 0.08,
                  "experience": 0.0, "education": 0.10}
    else:  # weak
        r_domain = rng.choice(ADJACENT[domain]) if rng.random() < 0.30 else \
            rng.choice([d for d in DOMAIN_SKILLS if d != domain])
        coverage = rng.uniform(0.0, 0.28)
        cand_years = rng.uniform(0, 8)
        edu = rng.choices([0, 1, 2, 3], weights=[10, 15, 55, 20])[0]
        r_seniority = rng.choice(seniorities)
        drop_p = {"summary": 0.30, "projects": 0.35, "skills": 0.15,
                  "experience": 0.0, "education": 0.20}
    return {"domain": r_domain, "coverage": coverage, "years": cand_years,
            "edu": edu, "seniority": r_seniority, "drop_p": drop_p}


def _title_relatedness(jd: dict, r_title: str, r_domain: str, r_seniority: str) -> float:
    if r_title == jd["title"]:
        return 1.0
    if r_domain == jd["domain"]:
        return 0.85 if r_seniority == jd["seniority"] else 0.65
    if r_domain in ADJACENT[jd["domain"]]:
        return 0.35
    return 0.10


def _make_resume(jd: dict, setup: dict) -> tuple[str, dict]:
    domain = setup["domain"]
    n_covered = round(setup["coverage"] * len(jd["req_skills"]))
    covered = rng.sample(jd["req_skills"], n_covered)
    extras = rng.sample(
        [s for s in DOMAIN_SKILLS[domain] if s not in covered],
        min(rng.randint(2, 5), len(DOMAIN_SKILLS[domain])),
    )
    skills = covered + extras
    rng.shuffle(skills)

    title = jd["title"] if (domain == jd["domain"] and setup["seniority"] == jd["seniority"]
                            and rng.random() < 0.45) \
        else rng.choice(TITLES[domain][setup["seniority"]])
    name = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
    email = f"{name.split()[0].lower()}.{name.split()[1].lower()}@example.com"

    keep = {s: rng.random() >= p for s, p in setup["drop_p"].items()}
    if setup["edu"] == 0:
        keep["education"] = False
    section_frac = (sum(keep.values()) + 1) / 6  # +1: contact header always present

    parts = [name, f"{email} | +91 9{rng.randint(100000000, 999999999)}", ""]
    if keep["summary"]:
        parts += ["SUMMARY",
                  f"{title} with {max(0.0, setup['years']):.0f} years of experience "
                  f"specializing in {skills[0]} and {skills[min(1, len(skills)-1)]}.", ""]
    if keep["skills"]:
        parts += ["SKILLS", ", ".join(_render_skill(s) for s in skills), ""]

    # Experience: split total years across 1-3 roles, newest first.
    parts += ["EXPERIENCE"]
    total_months = max(4, int(setup["years"] * 12))
    n_roles = min(rng.randint(1, 3), max(1, total_months // 12))
    cuts = sorted(rng.sample(range(1, total_months), n_roles - 1)) if n_roles > 1 else []
    spans = [b - a for a, b in zip([0] + cuts, cuts + [total_months])]
    end_y, end_m = REFERENCE_YEAR, REFERENCE_MONTH
    for i, months in enumerate(reversed(spans)):
        role_title = title if i == 0 else rng.choice(
            TITLES[domain][rng.choice(["junior", "mid"])])
        company = rng.choice(COMPANIES)
        dates = _date_range(end_y, end_m, months, latest=(i == 0))
        fmt = rng.random()
        if fmt < 0.6:
            parts.append(f"{role_title} | {company} | {dates}")
        else:
            parts.append(f"{role_title}, {company} ({dates})")
        used = rng.sample(skills, min(2, len(skills)))
        parts.append(f"- Delivered {domain} work using {used[0]} and {used[-1]}")
        gap = months + rng.randint(0, 2)
        end_m -= gap
        end_y += (end_m - 1) // 12
        end_m = (end_m - 1) % 12 + 1
    parts.append("")

    if keep["education"] and setup["edu"] > 0:
        degree = rng.choice(DEGREE_TEXT[setup["edu"]]).format(field=FIELDS[domain])
        parts += ["EDUCATION",
                  f"{degree}, {rng.choice(SCHOOLS)}, {rng.randint(2005, 2024)}", ""]
    if keep["projects"]:
        used = rng.sample(skills, min(2, len(skills)))
        parts += ["PROJECTS",
                  f"Built a {domain} project with {used[0]} and {used[-1]}.", ""]

    latents = {
        "skill_cov": len(covered) / len(jd["req_skills"]),
        "cand_years": setup["years"], "req_years": jd["req_years"],
        "edu_fit": 1.0 if setup["edu"] >= jd["req_edu"]
        else max(0.0, 1.0 - 0.32 * (jd["req_edu"] - setup["edu"])),
        "title_rel": _title_relatedness(jd, title, domain, setup["seniority"]),
        "section_frac": section_frac,
    }
    return "\n".join(parts), latents


def generate(n: int = 30000) -> pd.DataFrame:
    rows = []
    tiers = rng.choices(["strong", "moderate", "weak"], weights=[30, 40, 30], k=n)
    for i, tier in enumerate(tiers):
        domain = rng.choice(list(DOMAIN_SKILLS))
        seniority = rng.choice(list(SENIORITY_YEARS))
        jd = _make_jd(domain, seniority)
        resume_text, latents = _make_resume(jd, _pick_resume_setup(jd, tier))
        score = _rubric_score(latents)
        rows.append({
            "resume_text": resume_text, "jd_text": jd["text"],
            "score": round(score, 2), "label": score_to_label(score),
        })
        if (i + 1) % 1000 == 0:
            print(f"  generated {i + 1}/{n} pairs", flush=True)
    return pd.DataFrame(rows)


def main() -> None:
    print("=== Stage 1: synthetic dataset generation ===")
    df = generate(30000)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(DATASET_PATH, index=False)

    print(f"\nDataset shape: {df.shape}")
    print(f"Saved to: {DATASET_PATH}")
    print("\nLabel distribution:")
    dist = df["label"].value_counts()
    for label, count in dist.items():
        print(f"  {label:<13} {count:>5}  ({count / len(df):.1%})")
    print(f"\nScore stats: mean={df['score'].mean():.1f} "
          f"std={df['score'].std():.1f} min={df['score'].min():.1f} "
          f"max={df['score'].max():.1f}")

    print("\n=== 3 full sample rows ===")
    for idx in [0, 1, 2]:
        row = df.iloc[idx]
        print(f"\n--- sample {idx} | score={row['score']} | label={row['label']} ---")
        print("[RESUME]")
        print(row["resume_text"])
        print("[JOB DESCRIPTION]")
        print(row["jd_text"])


if __name__ == "__main__":
    main()
