"""Feature extraction from *raw* resume + job-description text.

The six features in the output contract are recomputed here from text only —
this module knows nothing about how the training data was generated (the
anti-leakage rule): no import of ml.generate_data anywhere below.
"""

import re

import numpy as np

from ml.common import (
    FEATURE_NAMES,
    REFERENCE_MONTH,
    REFERENCE_YEAR,
    SBERT_MODEL_NAME,
)
from ml.skills import (
    ALL_SKILLS,
    EDUCATION_KEYWORDS,
    EXPECTED_SECTIONS,
    SKILL_ALIASES,
)

_MONTHS = {
    m: i + 1
    for i, m in enumerate(
        "jan feb mar apr may jun jul aug sep oct nov dec".split()
    )
}

# "Jan 2020 - Present", "03/2019 - 07/2022", "2018 - 2021", en/em dashes too.
_RANGE_RE = re.compile(
    r"((?:[A-Za-z]{3,9}\.?\s+)?\d{4}|\d{1,2}/\d{4})\s*(?:-|–|—|to)\s*"
    r"((?:[A-Za-z]{3,9}\.?\s+)?\d{4}|\d{1,2}/\d{4}|present|current)",
    re.IGNORECASE,
)
_YEARS_PHRASE_RE = re.compile(r"(\d{1,2})\s*\+?\s*years?", re.IGNORECASE)
_TOKEN_RE = re.compile(r"[^\s,;:|/()\[\]]+")


def _is_adjacent_swap(a: str, b: str) -> bool:
    """True when b equals a except for one adjacent-character transposition
    ('python' vs 'pyhton') — the classic typing error, and the only kind of
    typo where same-length matching stays unambiguous."""
    if len(a) != len(b) or a == b:
        return False
    diff = [i for i, (x, y) in enumerate(zip(a, b)) if x != y]
    return (
        len(diff) == 2
        and diff[1] == diff[0] + 1
        and a[diff[0]] == b[diff[1]]
        and a[diff[1]] == b[diff[0]]
    )


def _parse_point(token: str) -> tuple[int, int] | None:
    """Parse one end of a date range into (year, month)."""
    token = token.strip().lower().rstrip(".")
    if token in ("present", "current"):
        return REFERENCE_YEAR, REFERENCE_MONTH
    if "/" in token:  # MM/YYYY
        month, year = token.split("/")
        return int(year), max(1, min(12, int(month)))
    parts = token.split()
    if len(parts) == 2:  # "Jan 2020"
        month = _MONTHS.get(parts[0][:3], 6)
        return int(parts[1]), month
    if token.isdigit() and len(token) == 4:  # bare year: assume mid-year
        return int(token), 6
    return None


class FeatureExtractor:
    """Turns (resume_text, jd_text) into the 6-dim feature vector.

    The TF-IDF vectorizer is fitted on training JDs only and pickled with
    the model bundle; the sentence-transformer is loaded lazily by name so
    the artifact stays small (< 50MB) and training/inference cannot drift.
    """

    def __init__(self):
        self.tfidf = None  # fitted in fit(); pickled with the bundle
        self._sbert = None
        self._emb_cache: dict[str, np.ndarray] = {}
        self._skill_patterns = None
        self._fuzzy_index = None
        self._analyzer = None
        self._vocab = None

    # -- pickling: drop lazy/heavy state, keep the fitted vectorizer -------

    def __getstate__(self):
        state = self.__dict__.copy()
        state["_sbert"] = None
        state["_emb_cache"] = {}
        state["_skill_patterns"] = None
        state["_fuzzy_index"] = None
        state["_analyzer"] = None
        state["_vocab"] = None
        return state

    # -- lazy helpers ------------------------------------------------------

    @property
    def skill_patterns(self) -> list[tuple[str, re.Pattern]]:
        """(canonical_name, compiled_regex) for every skill and alias."""
        if self._skill_patterns is None:
            pairs: list[tuple[str, str]] = [(s, s) for s in ALL_SKILLS]
            pairs += [(canon, alias) for alias, canon in SKILL_ALIASES.items()]
            self._skill_patterns = [
                (canon, re.compile(rf"(?<![\w+#]){re.escape(term)}(?![\w+#])", re.IGNORECASE))
                for canon, term in pairs
            ]
        return self._skill_patterns

    @property
    def fuzzy_index(self) -> dict[tuple[int, int], list[tuple[str, str]]]:
        """(word_count, char_len) -> [(canonical_name, lowercased term)] for
        every skill/alias of >= 4 chars; same-length bucketing keeps the
        typo scan cheap and precise."""
        if getattr(self, "_fuzzy_index", None) is None:
            pairs = [(s, s) for s in ALL_SKILLS]
            pairs += [(canon, alias) for alias, canon in SKILL_ALIASES.items()]
            index: dict[tuple[int, int], list[tuple[str, str]]] = {}
            for canon, term in pairs:
                low = " ".join(term.lower().split())
                if len(low) < 4:
                    continue
                index.setdefault((len(low.split()), len(low)), []).append((canon, low))
            self._fuzzy_index = index
        return self._fuzzy_index

    def _embed(self, text: str) -> np.ndarray:
        if self._sbert is None:
            from sentence_transformers import SentenceTransformer

            self._sbert = SentenceTransformer(SBERT_MODEL_NAME, device="cpu")
        key = text.strip().lower()
        if key not in self._emb_cache:
            self._emb_cache[key] = self._sbert.encode(
                [key], normalize_embeddings=True, show_progress_bar=False
            )[0]
        return self._emb_cache[key]

    # -- individual signals ------------------------------------------------

    def extract_skills(self, text: str) -> set[str]:
        exact = {canon for canon, pat in self.skill_patterns if pat.search(text)}
        return exact | self._fuzzy_skills(text, exact)

    def _fuzzy_skills(self, text: str, already_found: set[str]) -> set[str]:
        """Recover skill mentions the exact regexes miss because of a typo
        ('Pyhton', 'MachineL earning'): slide a window of the right word
        count over the text and accept same-length adjacent transpositions."""
        tokens = [t.lower().rstrip(".") for t in _TOKEN_RE.findall(text)]
        found: set[str] = set()
        for word_count in {wc for wc, _ in self.fuzzy_index}:
            for i in range(len(tokens) - word_count + 1):
                window = " ".join(tokens[i:i + word_count])
                for canon, term in self.fuzzy_index.get((word_count, len(window)), []):
                    if canon in already_found or canon in found:
                        continue
                    if _is_adjacent_swap(term, window):
                        found.add(canon)
        return found

    @staticmethod
    def extract_education_level(text: str) -> int:
        low = text.lower()
        for keyword, level in EDUCATION_KEYWORDS:
            if keyword in low:
                return level
        return 0

    @staticmethod
    def extract_resume_years(resume_text: str) -> float:
        """Total years of experience from date ranges (any format), with a
        'X years' phrase as fallback when no range parses."""
        total_months = 0
        for start_tok, end_tok in _RANGE_RE.findall(resume_text):
            start, end = _parse_point(start_tok), _parse_point(end_tok)
            if start and end:
                months = (end[0] - start[0]) * 12 + (end[1] - start[1])
                if 0 < months <= 50 * 12:
                    total_months += months
        if total_months == 0:
            phrase = _YEARS_PHRASE_RE.search(resume_text)
            return float(phrase.group(1)) if phrase else 0.0
        return total_months / 12.0

    @staticmethod
    def extract_required_years(jd_text: str) -> float:
        phrase = _YEARS_PHRASE_RE.search(jd_text)
        return float(phrase.group(1)) if phrase else 0.0

    @staticmethod
    def extract_jd_title(jd_text: str) -> str:
        for line in jd_text.splitlines():
            if line.lower().startswith("job title:"):
                return line.split(":", 1)[1].strip()
        for line in jd_text.splitlines():  # fallback: first non-empty line
            if line.strip():
                return line.strip()
        return ""

    @staticmethod
    def extract_latest_title(resume_text: str) -> str:
        """First role line under EXPERIENCE: 'Title | Company | Dates' or
        'Title, Company (Dates)'."""
        lines = resume_text.splitlines()
        in_exp = False
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.lower().startswith("experience"):
                in_exp = True
                continue
            if in_exp:
                if stripped.startswith("-"):
                    continue
                return re.split(r"[|,]", stripped)[0].strip()
        return ""

    # -- the six contract features ----------------------------------------

    def fit(self, jd_texts: list[str]) -> "FeatureExtractor":
        """Fit the TF-IDF vocabulary on *training* JDs only (no leakage)."""
        from sklearn.feature_extraction.text import TfidfVectorizer

        self.tfidf = TfidfVectorizer(stop_words="english", max_features=5000)
        self.tfidf.fit(jd_texts)
        return self

    def keyword_density(self, resume_text: str, jd_text: str) -> float:
        """TF-IDF-weighted fraction of JD keywords present in the resume
        (normalization by JD length comes from the TF-IDF weighting)."""
        if self.tfidf is None:
            raise RuntimeError("FeatureExtractor.fit() must run before use")
        if self._analyzer is None:  # cached: building these per call is ~100ms
            self._analyzer = self.tfidf.build_analyzer()
            self._vocab = self.tfidf.get_feature_names_out()
        jd_vec = self.tfidf.transform([jd_text])
        if jd_vec.nnz == 0:
            return 0.0
        resume_tokens = set(self._analyzer(resume_text))
        weights = jd_vec.tocoo()
        present = sum(
            w for j, w in zip(weights.col, weights.data)
            if self._vocab[j] in resume_tokens
        )
        return float(present / weights.data.sum())

    def extract(self, resume_text: str, jd_text: str) -> dict:
        """Full feature dict + supporting fields (missing skills, etc.)."""
        resume_skills = self.extract_skills(resume_text)
        jd_skills = self.extract_skills(jd_text)
        skill_overlap = (
            len(resume_skills & jd_skills) / len(jd_skills) if jd_skills else 0.0
        )

        # Asymmetric sigmoid: being short N years hurts ~3.5x more than
        # being over-qualified by N years helps (spec requirement).
        delta = self.extract_resume_years(resume_text) - self.extract_required_years(jd_text)
        slope = 0.9 if delta < 0 else 0.25
        experience_match = float(1.0 / (1.0 + np.exp(-(1.5 + slope * delta))))

        cand_edu = self.extract_education_level(resume_text)
        req_edu = self.extract_education_level(jd_text)
        education_match = (
            1.0 if cand_edu >= req_edu else max(0.0, 1.0 - 0.35 * (req_edu - cand_edu))
        )

        cand_title = self.extract_latest_title(resume_text)
        jd_title = self.extract_jd_title(jd_text)
        if cand_title and jd_title:
            cos = float(np.dot(self._embed(cand_title), self._embed(jd_title)))
            title_similarity = max(0.0, min(1.0, cos))
        else:
            title_similarity = 0.0

        low = resume_text.lower()
        section_completeness = sum(s in low for s in EXPECTED_SECTIONS) / len(EXPECTED_SECTIONS)

        features = {
            "skill_overlap": round(skill_overlap, 4),
            "experience_match": round(experience_match, 4),
            "education_match": round(education_match, 4),
            "title_similarity": round(title_similarity, 4),
            "keyword_density": round(self.keyword_density(resume_text, jd_text), 4),
            "section_completeness": round(section_completeness, 4),
        }
        missing = sorted(jd_skills - resume_skills)
        return {"features": features, "top_missing_skills": missing[:5]}

    def matrix(self, pairs: list[tuple[str, str]], log_every: int = 0) -> np.ndarray:
        """Feature matrix for many (resume, jd) pairs, in FEATURE_NAMES order."""
        rows = []
        for i, (resume, jd) in enumerate(pairs):
            feats = self.extract(resume, jd)["features"]
            rows.append([feats[name] for name in FEATURE_NAMES])
            if log_every and (i + 1) % log_every == 0:
                print(f"  features: {i + 1}/{len(pairs)} pairs", flush=True)
        return np.array(rows, dtype=float)
