"""Stage 3 — full evaluation of the saved artifact on the untouched test set.

Loads the bundle from disk (exactly what inference will use), rebuilds the
same stratified split as training, and reports MAE/RMSE/R2, the 3-label
confusion matrix, feature importances, the 5 worst misses with a hypothesis
each, and a calibration monotonicity check.

Run:  python -m ml.evaluate
"""

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    confusion_matrix,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)

from ml.common import ARTIFACT_PATH, DATASET_PATH, FEATURE_NAMES, score_to_label, split_dataset

LABELS = ["Weak Fit", "Moderate Fit", "Strong Fit"]


def _miss_hypothesis(row: pd.Series, feats: dict, err: float) -> str:
    """One-line guess at why this prediction missed."""
    if abs(row["score"] - 50) > 35 and abs(err) > 8:
        return "extreme true score — Gaussian label noise (sigma=4) likely pushed it past the rubric"
    if feats["skill_overlap"] < 0.2 and row["score"] > 50:
        return "skill extraction missed aliased/typo'd skills, so the model under-scored"
    if feats["experience_match"] > 0.85 and err < 0:
        return "over-qualified candidate: model rewards experience more than the rubric did here"
    if feats["title_similarity"] > 0.8 and err > 0:
        return "titles read as near-identical to the embedder but the rubric rated the pair lower"
    return "features sit near a label boundary where sigma=4 rubric noise dominates"


def main() -> None:
    print("=== Stage 3: evaluation on the untouched test set ===")
    bundle = joblib.load(ARTIFACT_PATH)
    model, fe = bundle["model"], bundle["extractor"]
    print(f"Loaded artifact: {ARTIFACT_PATH.name} (winner: {bundle['winner']})")

    df = pd.read_csv(DATASET_PATH)
    _, _, test_df = split_dataset(df)
    X = fe.matrix(list(zip(test_df["resume_text"], test_df["jd_text"])))
    y = test_df["score"].to_numpy()
    y_pred = np.clip(model.predict(X), 0, 100)

    mae = mean_absolute_error(y, y_pred)
    rmse = float(np.sqrt(mean_squared_error(y, y_pred)))
    r2 = r2_score(y, y_pred)
    print(f"\nTest metrics (n={len(y)}):")
    print(f"  MAE  = {mae:.3f}")
    print(f"  RMSE = {rmse:.3f}")
    print(f"  R2   = {r2:.4f}")

    true_labels = [score_to_label(s) for s in y]
    pred_labels = [score_to_label(s) for s in y_pred]
    cm = confusion_matrix(true_labels, pred_labels, labels=LABELS)
    acc = np.trace(cm) / cm.sum()
    print(f"\nConfusion matrix (rows=true, cols=predicted), accuracy={acc:.4f}:")
    header = " " * 14 + "".join(f"{l.split()[0]:>10}" for l in LABELS)
    print(header)
    for label, row in zip(LABELS, cm):
        print(f"  {label:<12}" + "".join(f"{v:>10}" for v in row))

    print("\nFeature importance ranking:")
    shares = bundle["importance_shares"]
    for name, share in sorted(shares.items(), key=lambda kv: -kv[1]):
        print(f"  {name:<21} {share:.3f}")

    print("\n5 worst predictions:")
    errors = y_pred - y
    worst = np.argsort(-np.abs(errors))[:5]
    for rank, i in enumerate(worst, 1):
        feats = dict(zip(FEATURE_NAMES, X[i].round(3)))
        row = test_df.iloc[i]
        print(f"  #{rank}: true={y[i]:.1f} pred={y_pred[i]:.1f} err={errors[i]:+.1f}")
        print(f"      features: {feats}")
        print(f"      hypothesis: {_miss_hypothesis(row, feats, errors[i])}")

    print("\nCalibration sanity check (mean predicted score per true label):")
    means = {}
    for label in LABELS:
        mask = np.array(true_labels) == label
        means[label] = float(y_pred[mask].mean())
        print(f"  {label:<13} mean predicted = {means[label]:.1f}")
    monotonic = means["Weak Fit"] < means["Moderate Fit"] < means["Strong Fit"]
    print(f"  monotonic (Weak < Moderate < Strong): {'PASS' if monotonic else 'FAIL'}")


if __name__ == "__main__":
    main()
