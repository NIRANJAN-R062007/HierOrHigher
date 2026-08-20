# HireOrHigher — working notes

React + Tailwind (Vite) frontend, FastAPI backend, Google Gemini, Supabase.
`README.md` covers what the product does; this file covers how to work in the repo.

## Commands

```bash
cd backend && ../.venv/bin/python -m pytest          # backend gate
cd frontend && npm run build                         # frontend gate (no JS test suite)

cd backend && ../.venv/bin/uvicorn app.main:app --reload --port 8000
cd frontend && npm run dev
.venv/bin/python scripts/seed.py                     # sample data, spends no Gemini quota
```

The venv is at the repo root (`.venv`), not in `backend/`. `.env` is at the repo root too —
`config.py` resolves it from `parents[2]`, so a `backend/.env` would be ignored entirely.

## Git workflow — strict

- Work on a feature branch. Don't merge to `main` or open a PR unless asked — push the branch and stop.
- **One file per commit.** Never bundle. A change touching six files is six commits, each with its
  own conventional-commit message.
- A new folder is committed *first* as a lone `.gitkeep`, then its files in follow-up commits.
  Every package directory here already has one.
- Push exactly once, as the very last action, after both gates pass. Never push mid-way to
  checkpoint work — if a test fails, fix and re-test locally on the same branch.

## Load-bearing conventions

**One Gemini key per module.** Four keys (`GEMINI_API_KEY_RESUME_PARSER`, `_GAP_MAPPER`,
`_INTERVIEW_GENERATOR`, `_PROFILE_OPTIMIZER`), mapped in `core/gemini.py:MODULE_KEYS` and exposed
as one `deps.get_*_gemini()` factory each. Quota isolation is the point: never share a key across
modules, and never add a fifth for a new feature — pick the module whose concern it belongs to.

**Prompt text lives in `app/prompts/*.txt`.** Never inline prompt strings. Load via
`load_prompt(name)` and pass every resume/JD through `wrap_untrusted()` before concatenating — those
tags are what the prompt files instruct the model to treat as data, so skipping them silently
removes the injection defense. A prompt edit belongs with the behavior change it serves (adjacent
commits, since one-file-per-commit rules out literally sharing one).

**Cache before Gemini.** Every service checks Supabase by content hash before spending a call —
resumes hash by file bytes, JDs by text, cross-module results by `combined_hash(resume, jd)`. The
check goes *before* text extraction and before the LLM, not after.

**`SupabaseRepository` is the only DB touchpoint.** Routes and services never call the Supabase
client directly. Add a method to `db/repository.py`, and a matching one to
`tests/fakes.py:FakeRepository`.

**ATS scoring stays rule-based** (`services/ats_scorer.py`) — deterministic, no LLM. Only the
*human* readability score is model-judged.

## Layering

```
api/routes/     HTTP shape, auth deps, error mapping — no business logic
services/       module logic; take `repo` and `gemini` as plain params
core/           gemini wrapper, hashing, prompt loader, file validation, rate limiter
models/         Pydantic contracts, doubling as Gemini structured-output schemas
db/repository.py  every Supabase read/write
```

Services receive `repo`/`gemini` as arguments rather than importing them; routes inject via
`Depends`. That indirection exists so tests can swap in fakes — keep it.

## Tests

`backend/tests/` runs each module end to end through `TestClient`. `conftest.py` sets dummy env
before `app.main` imports (config fails fast on missing keys) and overrides the auth, repository,
and Gemini deps. Fakes in `tests/fakes.py` are driven by `data/samples/dataset.json`, keyed off
persona names ("Asha Venkat", "Rohan Mehta") and companies ("CloudCore", "Metricly") — a new fake
response usually means a new dataset entry, not a hardcoded literal in the fake.

## Gotchas

**Gemini thinking tokens are drawn from `max_output_tokens`.** `generate_structured` sets
`thinking_budget: 0` unconditionally for exactly this reason. If a structured call returns truncated
JSON, check `usage_metadata.thoughts_token_count` before assuming the ceiling is too small — JD
extraction once burned 979 of its 1024 tokens thinking, left 30 for a 293-token answer, and
surfaced as a 502. Do not version-gate this on the model name; that is how it broke (`"2.5" in
model` stopped matching when the default moved to `gemini-3.5-flash`). Note `"pro"` tiers enforce a
non-zero thinking floor and would reject a zero budget outright.

**`GeminiClient` retries once, then raises `GeminiError` → 502.** A bad *config* therefore fails
twice and reads as an outage rather than degrading — worth remembering when a 502 appears
immediately after a config change.

**The Gemini free tier is ~20 requests per model per project per day.** Live verification scripts
exhaust it fast; a 429 mid-verify is usually quota, not the change under test. The four keys sit in
separate projects, so one exhausting doesn't affect the others.

**`candidates` and `applications` have RLS enabled with zero policies** — default-deny by
construction. Candidates are never authenticated and carry no `auth.uid()`, so every read goes
through an org-gated backend route. Don't add a policy to "fix" a blocked client-side read.

**Recruiter-side misses are all 404**, including "you aren't a member of this org" — registered once
in `main.py` so no handler can leak existence with a 403.

**The Vercel build needs `VITE_API_BASE_URL`.** Without it `lib/api.js` falls back to
`http://localhost:8000` and the live site only works next to a local backend.

**Secrets:** when displaying `.env`, pipe through `sed 's/=.*/=<value hidden>/'` so no key values
are printed.

Design tokens (ink / gold / paper, Fraunces + Inter) are in `tailwind.config.js`. The landing page
is dark on ink, the dashboard light on paper, and gold is the shared accent across both.
