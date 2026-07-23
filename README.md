<div align="center">

# HireOrHigher

**Know exactly where you stand.**

Upload one resume, paste one job description — and get an ATS score, a semantic skills-gap map, a tailored mock interview, and rewritten LinkedIn/portfolio copy, all on a single dashboard.

[![Live app](https://img.shields.io/badge/Live_app-hierorhigher.vercel.app-000000?style=flat-square&logo=vercel&logoColor=white)](https://hierorhigher.vercel.app/)

![React](https://img.shields.io/badge/React-20232A?style=flat-square&logo=react&logoColor=61DAFB)
![Vite](https://img.shields.io/badge/Vite-646CFF?style=flat-square&logo=vite&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-06B6D4?style=flat-square&logo=tailwindcss&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![Google Gemini](https://img.shields.io/badge/Google_Gemini-8E75B2?style=flat-square&logo=googlegemini&logoColor=white)
![Supabase](https://img.shields.io/badge/Supabase-3FCF8E?style=flat-square&logo=supabase&logoColor=white)

</div>

---

## Overview

HireOrHigher is an AI-powered career-readiness platform. A user uploads **one resume** and pastes **one job description**; four connected modules run against that single input and land on one dashboard.

Every module result is persisted in Supabase and keyed by content hash, so reloading the dashboard re-renders previous results with **zero** re-processing — and identical inputs never spend Gemini quota twice.

## ✨ Features

| # | Module | What it does |
|---|---|---|
| 1 | **Resume Parser + Score** | Structured parsing plus a dual score: a deterministic, rule-based ATS score and an LLM-judged human-readability score, each with a breakdown of what drove it. |
| 2 | **Gap-to-Job Mapper** | Embedding-based (semantic, not keyword) comparison of the parsed resume against the JD: matched skills, missing skills, match percentage. |
| 3 | **Mock Interview Generator** | 8–10 questions tagged Technical / Behavioral / Role-Fit, written from the candidate's actual projects, history, and identified gaps. |
| 4 | **LinkedIn / Portfolio Optimizer** | Headline, About section, and outcome-oriented project rewrites, each in Concise and Detailed tone variants. |

## 🧱 Tech stack

- **Frontend** — React + Tailwind, built with Vite
- **Backend** — FastAPI (Python)
- **AI** — Google Gemini (structured output + embeddings)
- **Data** — Supabase (PostgreSQL + Auth + Storage)

## 🏗️ Architecture & engineering notes

- **Caching:** resumes hash by file bytes, JDs by text, cross-module results by `sha256(resume_hash : jd_hash)` — every service checks Supabase before calling Gemini, so nothing is ever computed twice.
- **Prompt-injection defense:** resumes and JDs are wrapped in `<user_submitted_content>` tags, and every prompt file instructs the model to treat that content strictly as data.
- **Safe uploads:** content-type is verified by magic-byte inspection (not file extension), with a 5 MB cap, sanitized filenames, and a per-user sliding-window rate limit.
- **Resilient Gemini calls:** every call has a timeout and one retry; failures surface as a specific 502 the UI renders as an inline error state, and garbled parses (fewer than 2 structured fields) return a clear re-upload prompt.
- **Cohesive UI:** one design-token set (ink/gold/paper palette, Fraunces + Inter) shared by the cinematic dark landing page and the functional dashboard — animated score gauges, step-by-step loaders, skeletons, scroll-reveals, and reduced-motion support throughout.

## 📁 Repository layout

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
```

## Prerequisites

- Python 3.11+ · Node 18+ · a [Supabase](https://supabase.com) project · four Gemini API keys ([Google AI Studio](https://aistudio.google.com))

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

Integration tests run real sample resume/JD pairs from `data/samples/dataset.json` through the actual endpoints with a dataset-driven fake Gemini + in-memory repository (no network, no keys). They pin the acceptance criteria, including:

- both scores return with populated breakdowns;
- an identical re-upload is served from the content-hash cache with **no** Gemini call;
- the pair marked "should show 3 missing skills" returns exactly those 3;
- the gap mapper / interview / profile modules never re-call the parser;
- reloading the dashboard overview triggers zero Gemini calls.
