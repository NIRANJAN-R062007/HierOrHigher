"""Inference API for the Resume-to-Job Match Scorer.

The only module the backend imports. Loads the joblib bundle (model + fitted
FeatureExtractor) once and returns the exact output contract:

    match_score, label, confidence, breakdown{6 features}, top_missing_skills
"""

import numpy as np

from ml.common import (
    ARTIFACT_PATH,
    FEATURE_NAMES,
    MODERATE_THRESHOLD,
    STRONG_THRESHOLD,
    score_to_label,
)


class MatchScorer:
    """Loads the saved artifact and scores (resume_text, jd_text) pairs."""

    def __init__(self, artifact_path=ARTIFACT_PATH):
        import joblib

        if not artifact_path.exists():
            raise FileNotFoundError(f"model artifact missing: {artifact_path}")
        bundle = joblib.load(artifact_path)
        self.model = bundle["model"]
        self.extractor = bundle["extractor"]
        self.winner = bundle["winner"]

    def _confidence(self, x: np.ndarray, score: float) -> float:
        """Ensemble spread when the model exposes per-tree predictions
        (RandomForest); otherwise distance from the nearest label boundary.
        Both land in [0.30, 0.98] — low near the 40/70 cutoffs."""
        if hasattr(self.model, "estimators_"):
            per_tree = np.array([t.predict(x)[0] for t in self.model.estimators_])
            return float(np.clip(1.0 - per_tree.std() / 15.0, 0.30, 0.98))
        margin = min(abs(score - MODERATE_THRESHOLD), abs(score - STRONG_THRESHOLD))
        return float(np.clip(0.35 + margin / 25.0, 0.30, 0.98))

    def predict(self, resume_text: str, jd_text: str) -> dict:
        extracted = self.extractor.extract(resume_text, jd_text)
        feats = extracted["features"]
        x = np.array([[feats[name] for name in FEATURE_NAMES]], dtype=float)
        score = float(np.clip(self.model.predict(x)[0], 0.0, 100.0))
        confidence = self._confidence(x, score)
        return {
            "match_score": round(score, 2),
            "label": score_to_label(score),
            "confidence": round(confidence, 3),
            "breakdown": feats,
            "top_missing_skills": extracted["top_missing_skills"],
        }
