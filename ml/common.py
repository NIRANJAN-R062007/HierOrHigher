"""Shared constants and helpers for the match-scorer pipeline.

Everything here is used by both training and inference, so it must stay
free of any knowledge of the data generator's hidden rubric.
"""

from pathlib import Path

SEED = 42

# Fixed "today" so date-range parsing ("Jan 2024 - Present") is deterministic:
# same seed -> same features -> same model, per the engineering constraints.
REFERENCE_YEAR = 2026
REFERENCE_MONTH = 7

ML_DIR = Path(__file__).resolve().parent
DATA_DIR = ML_DIR / "data"
ARTIFACT_DIR = ML_DIR / "artifacts"
DATASET_PATH = DATA_DIR / "dataset.csv"
ARTIFACT_PATH = ARTIFACT_DIR / "match_scorer.joblib"

SBERT_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

FEATURE_NAMES = [
    "skill_overlap",
    "experience_match",
    "education_match",
    "title_similarity",
    "keyword_density",
    "section_completeness",
]

STRONG_THRESHOLD = 70.0
MODERATE_THRESHOLD = 40.0


def score_to_label(score: float) -> str:
    """Map a 0-100 score to the 3-class label (Strong >= 70, Moderate 40-69)."""
    if score >= STRONG_THRESHOLD:
        return "Strong Fit"
    if score >= MODERATE_THRESHOLD:
        return "Moderate Fit"
    return "Weak Fit"


def split_dataset(df, seed: int = SEED):
    """80/10/10 train/val/test split, stratified by label.

    Single source of truth so train.py and evaluate.py can never disagree
    about which rows are held out.
    """
    from sklearn.model_selection import train_test_split

    train_df, hold = train_test_split(
        df, test_size=0.20, random_state=seed, stratify=df["label"]
    )
    val_df, test_df = train_test_split(
        hold, test_size=0.50, random_state=seed, stratify=hold["label"]
    )
    return train_df, val_df, test_df
