"""Stage 4 — fresh-process inference verification.

Run as its own process (python -m ml.verify_inference) so the model is loaded
cold from disk, exactly as the API will at startup. Scores three handwritten
cases and measures single-prediction latency (< 500ms gate, CPU only).
"""

import json
import time

from ml.inference import MatchScorer

STRONG_RESUME = """Asha Venkat
asha.venkat@example.com | +91 9812345678

SUMMARY
Senior Software Engineer with 8 years of experience building Python backend services.

SKILLS
Python, FastAPI, Django, PostgreSQL, Redis, Docker, Kubernetes, AWS, Git, CI/CD, REST APIs, Linux, Microservices

EXPERIENCE
Senior Software Engineer | CloudCore | Mar 2021 - Present
- Built Python microservices with FastAPI, PostgreSQL and Redis on AWS
Software Engineer | Metricly | 06/2018 - 02/2021
- Developed Django REST APIs and CI/CD pipelines with Docker

EDUCATION
B.Tech in Computer Science, Anna University, 2018

PROJECTS
Open-source contributor to a Python task queue built on Redis and Kubernetes.
"""

STRONG_JD = """Job Title: Senior Software Engineer
Company: NovaWorks

About the Role:
We are hiring a Senior Software Engineer to build Python backend services.

Requirements:
- 5+ years of relevant experience
- Proficiency in: Python, FastAPI, PostgreSQL, Docker, Kubernetes, AWS, REST APIs, CI/CD
- Bachelor's degree in a relevant field required

Responsibilities:
- Design and ship Python microservices
- Mentor mid-level engineers
"""

WEAK_RESUME = """Meera Nair
meera.nair@example.com | +91 9898989898

SUMMARY
Graphic and brand designer with 4 years of experience crafting visual identities.

SKILLS
Adobe Photoshop, Adobe Illustrator, Figma, Typography, Branding, Motion Design

EXPERIENCE
UI Designer | PixelForge | Jan 2022 - Present
- Designed brand systems and marketing collateral in Illustrator and Figma

EDUCATION
Bachelor of Science in Design, SRM University, 2021
"""

WEAK_JD = """Job Title: Backend Developer
Company: FinEdge

About the Role:
We are hiring a Backend Developer for our payments platform.

Requirements:
- 4+ years of relevant experience
- Proficiency in: Java, Go, PostgreSQL, Redis, Kubernetes, Microservices, SQL, Linux
- Master's degree required

Responsibilities:
- Build low-latency payment services
"""

AMBIGUOUS_RESUME = """Rohan Mehta
rohan.mehta@example.com | +91 9765432109

SUMMARY
Financial analyst transitioning into data science after 3 years in equity research.

SKILLS
Excel, SQL, Python, Statistics, Financial Modeling, Tableau, Forecasting

EXPERIENCE
Financial Analyst | BlueLedger | 2023 - Present
- Built forecasting models in Excel and Python; automated reporting with SQL

EDUCATION
MBA, BITS Pilani, 2022

PROJECTS
Kaggle-style churn prediction project using Python and Statistics.
"""

AMBIGUOUS_JD = """Job Title: Data Scientist
Company: DataSpring

About the Role:
We are hiring a Data Scientist to drive experimentation and modeling.

Requirements:
- 3+ years of relevant experience
- Proficiency in: Python, SQL, Machine Learning, Pandas, Scikit-learn, Statistics, A/B Testing, Tableau
- Master's degree required

Responsibilities:
- Build and ship predictive models
"""

CASES = [
    ("1. obvious STRONG match (senior Python dev vs Python JD)", STRONG_RESUME, STRONG_JD),
    ("2. obvious WEAK match (graphic designer vs backend JD)", WEAK_RESUME, WEAK_JD),
    ("3. AMBIGUOUS middle (finance -> data science switcher)", AMBIGUOUS_RESUME, AMBIGUOUS_JD),
]


def main() -> None:
    print("=== Stage 4: fresh-process inference verification ===")
    t0 = time.perf_counter()
    scorer = MatchScorer()
    print(f"Artifact loaded cold from disk in {time.perf_counter() - t0:.2f}s "
          f"(winner: {scorer.winner})")

    scores = []
    for name, resume, jd in CASES:
        result = scorer.predict(resume, jd)
        scores.append(result["match_score"])
        print(f"\n--- {name} ---")
        print(json.dumps(result, indent=2))

    ordered = scores[0] > scores[2] > scores[1]
    print(f"\nOrdering check strong({scores[0]}) > ambiguous({scores[2]}) > "
          f"weak({scores[1]}): {'PASS' if ordered else 'FAIL'}")

    # Latency: warm-up already happened above; time single predictions.
    times = []
    for _ in range(10):
        t = time.perf_counter()
        scorer.predict(AMBIGUOUS_RESUME, AMBIGUOUS_JD)
        times.append((time.perf_counter() - t) * 1000)
    import numpy as np

    print(f"\nSingle-prediction latency over 10 runs: "
          f"mean={np.mean(times):.1f}ms p95={np.percentile(times, 95):.1f}ms "
          f"(gate < 500ms: {'PASS' if np.mean(times) < 500 else 'FAIL'})")


if __name__ == "__main__":
    main()
