"""Feature extraction from *raw* resume + job-description text.

The nine features in the output contract are recomputed here from text only —
this module knows nothing about how the training data was generated (the
anti-leakage rule): no import of ml.generate_data anywhere below.
"""

import re

import numpy as np

from ml.common import (
    ARTIFACT_DIR,
    FEATURE_NAMES,
    REFERENCE_MONTH,
    REFERENCE_YEAR,
)
from ml.skills import (
    ALL_SKILLS,
    EDUCATION_KEYWORDS,
    EXPECTED_SECTIONS,
    SECTION_SYNONYMS,
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
# "8 years", "8+ yrs", and the lower bound of ranges like "4-6 years".
_YEARS_PHRASE_RE = re.compile(
    r"(\d{1,2})\s*(?:[-–]\s*\d{1,2}\s*)?\+?\s*(?:years?|yrs?)", re.IGNORECASE
)
_TOKEN_RE = re.compile(r"[^\s,;:|/()\[\]]+")
_JD_TITLE_PREFIXES = ("job title:", "position:", "role:")
_EXPERIENCE_HEADERS = tuple(SECTION_SYNONYMS["experience"])

# Ordinal seniority ladder read off job titles (0=entry .. 3=lead). Checked
# in order so "Lead"/"Head" outranks a stray "Senior" in the same title.
_SENIORITY_TIERS: list[tuple[tuple[str, ...], int]] = [
    (("staff", "principal", "lead", "head of", "director", "chief", "vp"), 3),
    (("senior", "sr.", "sr "), 2),
    (("intern", "trainee", "junior", "jr.", "jr ", "associate", "coordinator"), 0),
]
_SEMANTIC_CHARS = 1200  # embed only the head of each text: cheap and salient

# Committed ONNX export of all-MiniLM-L6-v2 (see ml/export_onnx.py). Loaded via
# onnxruntime + tokenizers so inference never pulls in torch/sentence-transformers
# or downloads from HuggingFace — that path OOM-kills Render's 512MB free tier.
_ONNX_MODEL_PATH = ARTIFACT_DIR / "onnx" / "model.onnx"
_ONNX_TOKENIZER_PATH = ARTIFACT_DIR / "onnx" / "tokenizer.json"
_MAX_SEQ_LENGTH = 256  # sentence_bert_config.json for this model


def _seniority_level(title: str) -> int:
    low = title.lower()
    for keywords, level in _SENIORITY_TIERS:
        if any(k in low for k in keywords):
            return level
    return 1  # unmarked titles read as mid-level


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


def _is_inner_deletion(term: str, window: str) -> bool:
    """True when window equals term with one non-edge character removed
    ('python' vs 'pythn'). Edge characters stay excluded so plurals and
    prefixes ('spark'/'sparks') never false-positive."""
    if len(window) != len(term) - 1 or len(term) < 5:
        return False
    return any(term[:i] + term[i + 1:] == window for i in range(1, len(term) - 1))


def _is_inner_doubling(term: str, window: str) -> bool:
    """True when window equals term with one non-edge character doubled
    ('python' vs 'pythhon')."""
    if len(window) != len(term) + 1 or len(term) < 4:
        return False
    return any(
        term[:i + 1] + term[i] + term[i + 1:] == window
        for i in range(1, len(term) - 1)
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
        self._session = None  # lazy onnxruntime InferenceSession
        self._tokenizer = None  # lazy tokenizers.Tokenizer
        self._emb_cache: dict[str, np.ndarray] = {}
        self._skill_patterns = None
        self._fuzzy_index = None
        self._analyzer = None
        self._vocab = None

    # -- pickling: drop lazy/heavy state, keep the fitted vectorizer -------

    def __getstate__(self):
        state = self.__dict__.copy()
        state["_session"] = None
        state["_tokenizer"] = None
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
        """384-dim unit embedding via ONNX Runtime, reproducing the
        sentence-transformers pipeline: WordPiece tokenization, attention-mask
        mean pooling over last_hidden_state, then L2 normalization. Callers rely
        on the vector being unit-length (they use np.dot as cosine)."""
        # getattr guard so a FeatureExtractor unpickled from an artifact saved
        # before this attribute existed (e.g. the committed match_scorer.joblib)
        # still initializes the session lazily — same pattern as fuzzy_index.
        if getattr(self, "_session", None) is None:
            import onnxruntime as ort
            from tokenizers import Tokenizer

            self._session = ort.InferenceSession(
                str(_ONNX_MODEL_PATH), providers=["CPUExecutionProvider"]
            )
            self._tokenizer = Tokenizer.from_file(str(_ONNX_TOKENIZER_PATH))
            self._tokenizer.enable_truncation(max_length=_MAX_SEQ_LENGTH)
        key = text.strip().lower()
        if key not in self._emb_cache:
            enc = self._tokenizer.encode(key)
            ids = np.array([enc.ids], dtype=np.int64)
            mask = np.array([enc.attention_mask], dtype=np.int64)
            (hidden,) = self._session.run(
                ["last_hidden_state"],
                {
                    "input_ids": ids,
                    "attention_mask": mask,
                    "token_type_ids": np.zeros_like(ids),
                },
            )
            weights = mask[0][:, None].astype(np.float32)
            pooled = (hidden[0] * weights).sum(0) / np.clip(weights.sum(), 1e-9, None)
            norm = float(np.linalg.norm(pooled))
            self._emb_cache[key] = (pooled / max(norm, 1e-12)).astype(np.float32)
        return self._emb_cache[key]

    # -- individual signals ------------------------------------------------

    def extract_skills(self, text: str) -> set[str]:
        exact = {canon for canon, pat in self.skill_patterns if pat.search(text)}
        return exact | self._fuzzy_skills(text, exact)

    def _fuzzy_skills(self, text: str, already_found: set[str]) -> set[str]:
        """Recover skill mentions the exact regexes miss because of a typo:
        an adjacent swap ('Pyhton', 'MachineL earning'), a dropped inner
        character ('Pythn'), or a doubled inner character ('Pythhon'). Slide
        a window of the right word count over the text and match against
        length-bucketed terms."""
        tokens = [t.lower().rstrip(".") for t in _TOKEN_RE.findall(text)]
        found: set[str] = set()
        for word_count in {wc for wc, _ in self.fuzzy_index}:
            for i in range(len(tokens) - word_count + 1):
                window = " ".join(tokens[i:i + word_count])
                # Bucket to search x typo check: swap keeps length, a window
                # missing a char is one shorter than its term, and so on.
                probes = (
                    (len(window), _is_adjacent_swap),
                    (len(window) + 1, _is_inner_deletion),
                    (len(window) - 1, _is_inner_doubling),
                )
                for term_len, check in probes:
                    for canon, term in self.fuzzy_index.get((word_count, term_len), []):
                        if canon in already_found or canon in found:
                            continue
                        if check(term, window):
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
            if line.lower().startswith(_JD_TITLE_PREFIXES):
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
            if stripped.lower().startswith(_EXPERIENCE_HEADERS):
                in_exp = True
                continue
            if in_exp:
                if stripped.startswith("-"):
                    continue
                return re.split(r"[|,]", stripped)[0].strip()
        return ""

    # -- the nine contract features ---------------------------------------

    def fit(self, jd_texts: list[str]) -> "FeatureExtractor":
        """Fit the TF-IDF vocabulary on *training* JDs only (no leakage)."""
        from sklearn.feature_extraction.text import TfidfVectorizer

        self.tfidf = TfidfVectorizer(stop_words="english", max_features=5000)
        self.tfidf.fit(jd_texts)
        return self

    def keyword_density(self, resume_text: str, jd_text: str) -> float:
        """TF-IDF-weighted fraction of JD keywords present in the resume
        (normalization by JD length comes from the TF-IDF weighting).
        A JD keyword also counts when the resume spells it with one
        adjacent-character typo, mirroring extract_skills."""
        if self.tfidf is None:
            raise RuntimeError("FeatureExtractor.fit() must run before use")
        if self._analyzer is None:  # cached: building these per call is ~100ms
            self._analyzer = self.tfidf.build_analyzer()
            self._vocab = self.tfidf.get_feature_names_out()
        jd_vec = self.tfidf.transform([jd_text])
        if jd_vec.nnz == 0:
            return 0.0
        resume_tokens = set(self._analyzer(resume_text))
        tokens_by_len: dict[int, list[str]] = {}
        for tok in resume_tokens:
            tokens_by_len.setdefault(len(tok), []).append(tok)
        weights = jd_vec.tocoo()
        present = 0.0
        for j, w in zip(weights.col, weights.data):
            term = self._vocab[j]
            if term in resume_tokens or (
                len(term) >= 4
                and (
                    any(_is_adjacent_swap(term, tok)
                        for tok in tokens_by_len.get(len(term), ()))
                    or any(_is_inner_deletion(term, tok)
                           for tok in tokens_by_len.get(len(term) - 1, ()))
                    or any(_is_inner_doubling(term, tok)
                           for tok in tokens_by_len.get(len(term) + 1, ()))
                )
            ):
                present += w
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
        section_completeness = sum(
            any(syn in low for syn in SECTION_SYNONYMS[name])
            for name in EXPECTED_SECTIONS
        ) / len(EXPECTED_SECTIONS)

        # Raw signed gap in years, scaled to [-1, 1]: keeps the resolution
        # the sigmoid squashes away at the extremes.
        experience_gap = float(np.clip(delta, -10.0, 10.0)) / 10.0

        # Whole-text semantic similarity: catches domain relatedness the
        # title comparison misses (career switchers, odd titles).
        sem = float(np.dot(
            self._embed(resume_text[:_SEMANTIC_CHARS]),
            self._embed(jd_text[:_SEMANTIC_CHARS]),
        ))
        semantic_similarity = max(0.0, min(1.0, sem))

        # How far apart the two titles sit on the seniority ladder.
        if cand_title and jd_title:
            seniority_alignment = 1.0 - abs(
                _seniority_level(cand_title) - _seniority_level(jd_title)
            ) / 3.0
        else:
            seniority_alignment = 0.5  # unknown: neither aligned nor opposed

        features = {
            "skill_overlap": round(skill_overlap, 4),
            "experience_match": round(experience_match, 4),
            "education_match": round(education_match, 4),
            "title_similarity": round(title_similarity, 4),
            "keyword_density": round(self.keyword_density(resume_text, jd_text), 4),
            "section_completeness": round(section_completeness, 4),
            "experience_gap": round(experience_gap, 4),
            "semantic_similarity": round(semantic_similarity, 4),
            "seniority_alignment": round(seniority_alignment, 4),
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
