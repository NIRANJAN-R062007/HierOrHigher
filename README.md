# HireOrHigher

AI-powered career-readiness platform. A user uploads **one resume** and pastes **one job description** — four connected modules run against that single input and land on one dashboard:

1. **Resume Parser + Score** — structured parsing plus a dual score: a deterministic, rule-based ATS score and an LLM-judged human-readability score, each with a breakdown of what drove it.
2. **Gap-to-Job Mapper** — embedding-based (semantic, not keyword) comparison of the parsed resume against the JD: matched skills, missing skills, match percentage.
3. **Mock Interview Generator** — 8–10 questions tagged Technical / Behavioral / Role-Fit, written from the candidate's actual projects, history, and identified gaps.
4. **LinkedIn / Portfolio Optimizer** — headline, About section, and outcome-oriented project rewrites, each in Concise and Detailed tone variants.

Every module result is persisted in Supabase and keyed by content hash, so reloading the dashboard re-renders previous results with **zero** re-processing, and identical inputs never spend Gemini quota twice.

**Stack:** React + Tailwind (Vite) · FastAPI (Python) · Google Gemini · Supabase (PostgreSQL + Auth + Storage)

---

## Repository layout

```
backend/
  app/
    api/routes/     # one route file per feature area (health, resumes, gap, interviews, profiles)
    api/deps.py     # auth, repository, per-module Gemini clients, rate limit
    core/           # Gemini wrapper (timeout + retry-once), hashing, file validation, prompt loader
    db/             # Supabase client + repository (the only DB touchpoint)
    models/         # Pydantic contracts — the exact request/response shapes
    prompts/        # versioned Gemini prompt files, one per module (never inline strings)
    services/       # one service per module's Gemini-calling logic + rule-based ATS scorer
  tests/            # integration tests per module, driven by the sample dataset
supabase/migrations/  # SQL migrations — RLS enabled in the same file as each CREATE TABLE
scripts/seed.py       # loads the sample dataset for an instant, Gemini-free demo
data/samples/         # sample resumes + JDs (test fixtures and seed source)
frontend/             # Vite + React + Tailwind app (landing, auth, dashboard)
ml/                   # isolated ML package: offline resume-to-job match scorer
```

## Prerequisites

- Python 3.11+ · Node 18+ · a [Supabase](https://supabase.com) project · four Gemini API keys ([Google AI Studio](https://aistudio.google.com))

## Setup

### 1. Environment variables

Copy the templates and fill in values (names only are documented in the templates — no real values are ever committed):

```bash
cp .env.example .env                      # backend (repo root)
cp frontend/.env.example frontend/.env    # frontend
```

Required backend variables (validated at startup — the app refuses to boot and names any missing one):

| Variable | Purpose |
|---|---|
| `GEMINI_API_KEY_RESUME_PARSER` | Module 5.1 — dedicated key |
| `GEMINI_API_KEY_GAP_MAPPER` | Module 5.2 — dedicated key |
| `GEMINI_API_KEY_INTERVIEW_GENERATOR` | Module 5.3 — dedicated key |
| `GEMINI_API_KEY_PROFILE_OPTIMIZER` | Module 5.4 — dedicated key |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Server-side Supabase key |

One key **per module** keeps quota, rate limits, and cost isolated — one module hitting a limit never blocks the others. Frontend variables: `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `VITE_API_BASE_URL`.

### 2. Database

Apply the migrations in `supabase/migrations/` in numeric order (Supabase SQL editor, or `supabase db push` with the CLI). Every table ships with Row Level Security enabled in the same migration that creates it — users can only ever read/write their own rows.

### 3. Backend

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
cd backend
uvicorn app.main:app --reload        # http://localhost:8000 — OpenAPI docs at /docs
```

### 4. Frontend

```bash
cd frontend
npm install
npm run dev                          # http://localhost:5173
```

## Seeding demo data

Loads the sample dataset (two personas with all four module results) straight into Supabase, so a review demo shows populated results instantly — no live uploads, no waiting on Gemini:

```bash
.venv/bin/python scripts/seed.py
```

The script is idempotent, prints the demo login (`demo@hireorhigher.dev` / `DEMO_USER_PASSWORD` env var, with a default it prints), and recomputes the ATS score with the real rule-based scorer so seeded rows match live behavior exactly.

## Tests

```bash
cd backend && ../.venv/bin/python -m pytest
```

Integration tests run real sample resume/JD pairs from `data/samples/dataset.json` through the actual endpoints with a dataset-driven fake Gemini + in-memory repository (no network, no keys). They pin the spec's acceptance criteria, including:

- both scores return with populated breakdowns;
- an identical re-upload is served from the content-hash cache with **no** Gemini call;
- the pair marked "should show 3 missing skills" returns exactly those 3;
- the gap mapper / interview / profile modules never re-call the parser;
- reloading the dashboard overview triggers zero Gemini calls.

## ML: offline Resume-to-Job Match Scorer

`POST /ml/score` predicts how well a resume matches a JD — score 0–100, a
Strong/Moderate/Weak label, per-feature breakdown, and up to 5 missing skills —
with **no Gemini call**. The Gap-to-Job Mapper uses it for fast, free scoring and
only escalates to Gemini when the response carries `recommend_gemini_review: true`
(confidence < 0.6 or score in the ambiguous 45–55 band).

**Architecture decisions**

- **Feature-based regression, not end-to-end text models.** Six engineered
  features (skill overlap with alias resolution, asymmetric-sigmoid experience
  match, ordinal education match, MiniLM title cosine, TF-IDF keyword density,
  section completeness) feed a tuned XGBoost regressor. On synthetic-but-noisy
  data this beat a Ridge baseline honestly (5-fold CV MAE 5.42 vs 5.75) and the
  breakdown in the API response falls straight out of the feature vector.
- **One bundled artifact.** Model + fitted TF-IDF vectorizer travel in a single
  joblib file (~0.14 MB), so training and inference can never drift apart. The
  sentence-transformer is referenced by name and loaded lazily at startup.
- **Anti-leakage by construction.** The dataset generator's hidden scoring
  rubric lives only in `ml/generate_data.py`; training and inference recompute
  every feature from raw text and never import the generator.
- **Graceful degradation.** The model loads once via the FastAPI lifespan hook;
  a missing/corrupt artifact turns `/ml/score` into a clear 503 without touching
  the Gemini modules. Results are cached in `ml_score_cache` (migration 0008)
  keyed by `sha256(resume_text + job_description)`, mirroring the
  check-cache-before-Gemini strategy.
- **CPU-only and deterministic**: fixed seed 42 end-to-end, single-prediction
  latency ~3 ms, all ML dependencies isolated in `ml/requirements.txt`.

Held-out test set (500 pairs): **R² 0.923 · MAE 5.2 · label accuracy 87%**,
no feature above 46% importance, calibration monotonic across labels.

**Retrain from scratch (3 commands, repo root):**

```bash
pip install -r ml/requirements.txt
python -m ml.generate_data          # 5,000 synthetic resume/JD pairs -> ml/data/
python -m ml.train                  # compare Ridge/RF/XGBoost, tune, gate, save artifact
```

Then verify with `python -m ml.evaluate` and `python -m ml.verify_inference`.
macOS note: if the process dies silently during training, xgboost and torch are
fighting over OpenMP — point xgboost's rpath at torch's bundled libomp
(`install_name_tool -rpath /opt/homebrew/opt/libomp/lib <venv>/lib/python3*/site-packages/torch/lib <venv>/lib/python3*/site-packages/xgboost/lib/libxgboost.dylib`
then `codesign -f -s -` the same dylib).

## Design & engineering notes

- **Caching (spec 3.3):** resumes hash by file bytes, JDs by text, cross-module results by `sha256(resume_hash : jd_hash)` — every service checks Supabase before calling Gemini.
- **Prompt injection (spec 4):** resumes/JDs are wrapped in `<user_submitted_content>` tags and every prompt file instructs the model to treat that content strictly as data.
- **Uploads (spec 4):** content-type by magic-byte inspection (not extension), 5MB cap, sanitized filenames, per-user sliding-window rate limit.
- **Errors (spec 9):** every Gemini call has a timeout and one retry; failures surface as a specific 502 the UI renders as an inline error state; garbled parses (<2 structured fields) return a clear re-upload prompt.
- **UI:** one design-token set (ink/gold/paper palette, Fraunces + Inter) shared by the cinematic dark landing page and the light, functional dashboard; animated score gauges, step-by-step loaders, skeletons, scroll-reveals, and reduced-motion support throughout.
