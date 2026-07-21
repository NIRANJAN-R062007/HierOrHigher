"""Parity check: the ONNX embedding path vs the old sentence-transformers path.

Run as its own process:

    python -m ml.verify_onnx

Confirms the ONNX Runtime embeddings in ml/features.py reproduce the torch/
sentence-transformers embeddings the committed match_scorer.joblib was trained on
closely enough that scores are unchanged — not just that inference runs. Needs
torch + sentence-transformers installed (dev only) to compute the reference; the
production path (onnxruntime + tokenizers) needs neither. Reports PASS/FAIL on:
  * per-string embedding cosine (ONNX vs sentence-transformers), and
  * match_score delta on handwritten + real dataset rows, plus score ordering.
"""

import csv
import random

import numpy as np

from ml.common import DATASET_PATH, SBERT_MODEL_NAME
from ml.features import FeatureExtractor
from ml.inference import MatchScorer
from ml.verify_inference import CASES  # 3 handwritten strong/weak/ambiguous pairs

COSINE_MIN = 0.999  # fp32 export should be ~1.0; well above any real drift
SCORE_TOL = 1.0     # max acceptable |match_score| difference, in points

# Texts spanning what _embed() actually sees: titles and text heads.
EMBED_TEXTS = [
    "Senior Software Engineer",
    "Data Scientist",
    "Backend Developer",
    "python fastapi postgresql docker kubernetes aws rest apis ci/cd microservices",
    "graphic and brand designer figma illustrator typography motion design",
    "",
]


def _reference_embedder():
    """The old path: sentence-transformers, normalized — the training ground truth."""
    from sentence_transformers import SentenceTransformer

    sbert = SentenceTransformer(SBERT_MODEL_NAME, device="cpu")
    cache: dict[str, np.ndarray] = {}

    def embed(text: str) -> np.ndarray:
        key = text.strip().lower()
        if key not in cache:
            cache[key] = sbert.encode(
                [key], normalize_embeddings=True, show_progress_bar=False
            )[0]
        return cache[key]

    return embed


def _sample_rows(n: int = 5) -> list[tuple[str, str]]:
    """A handful of real (resume, jd) pairs from the dataset, if present."""
    if not DATASET_PATH.exists():
        return []
    with DATASET_PATH.open(newline="") as f:
        rows = [(r["resume_text"], r["jd_text"]) for r in csv.DictReader(f)]
    random.seed(0)
    return random.sample(rows, min(n, len(rows)))


def main() -> None:
    print("=== ONNX vs sentence-transformers embedding parity ===")
    ref_embed = _reference_embedder()
    onnx = FeatureExtractor()

    # 1. Direct embedding cosine.
    cosines = []
    for text in EMBED_TEXTS:
        a = onnx._embed(text)
        b = ref_embed(text)
        cos = float(np.dot(a, b))
        cosines.append(cos)
        print(f"  cosine={cos:.6f}  '{text[:48]}'")
    emb_ok = min(cosines) >= COSINE_MIN
    print(f"embedding cosine min={min(cosines):.6f} "
          f"(gate >= {COSINE_MIN}): {'PASS' if emb_ok else 'FAIL'}")

    # 2. End-to-end match_score parity: same model + extractor, ONNX vs reference
    #    embeddings, so any score drift is attributable purely to the swap.
    scorer = MatchScorer()
    ext = scorer.extractor
    real_embed = ext._embed  # the ONNX bound method

    def score(resume: str, jd: str, embed_fn) -> float:
        ext._embed = embed_fn
        ext._emb_cache = {}
        return scorer.predict(resume, jd)["match_score"]

    cases = [(name, r, j) for name, r, j in CASES]
    cases += [(f"dataset row {i}", r, j) for i, (r, j) in enumerate(_sample_rows())]

    deltas, onnx_scores = [], []
    print("\n  case                                        onnx    ref   delta")
    for name, resume, jd in cases:
        s_onnx = score(resume, jd, real_embed)
        s_ref = score(resume, jd, ref_embed)
        deltas.append(abs(s_onnx - s_ref))
        onnx_scores.append(s_onnx)
        print(f"  {name[:42]:42s} {s_onnx:6.2f} {s_ref:6.2f} {s_onnx - s_ref:+6.2f}")
    ext._embed = real_embed

    score_ok = max(deltas) <= SCORE_TOL
    print(f"\nmax |match_score delta| = {max(deltas):.3f} "
          f"(gate <= {SCORE_TOL}): {'PASS' if score_ok else 'FAIL'}")

    # 3. Ordering on the three handwritten cases (strong > ambiguous > weak).
    strong, weak, ambiguous = onnx_scores[0], onnx_scores[1], onnx_scores[2]
    order_ok = strong > ambiguous > weak
    print(f"ordering strong({strong:.1f}) > ambiguous({ambiguous:.1f}) > "
          f"weak({weak:.1f}): {'PASS' if order_ok else 'FAIL'}")

    ok = emb_ok and score_ok and order_ok
    print(f"\nOVERALL: {'PASS' if ok else 'FAIL'}")
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
