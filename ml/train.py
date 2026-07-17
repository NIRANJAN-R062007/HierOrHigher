"""Stage 2 — train, compare, tune, and bundle the match scorer.

Reads the raw-text dataset (never the generator's rubric), recomputes the six
contract features, compares Ridge / RandomForest / XGBoost with 5-fold CV,
tunes the best tree model with RandomizedSearchCV, and saves ONE joblib
bundle (model + fitted FeatureExtractor) so preprocessing can never drift
from inference.

Run:  python -m ml.train
"""

import time

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import accuracy_score, mean_absolute_error, r2_score
from sklearn.model_selection import KFold, RandomizedSearchCV, cross_val_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor

from ml.common import (
    ARTIFACT_DIR,
    ARTIFACT_PATH,
    DATASET_PATH,
    FEATURE_NAMES,
    SEED,
    score_to_label,
    split_dataset,
)
from ml.features import FeatureExtractor


FEATURES_CACHE = DATASET_PATH.with_name("features_cache.npz")


def build_features(df: pd.DataFrame, fe: FeatureExtractor, name: str) -> np.ndarray:
    print(f"Extracting features for {name} ({len(df)} pairs)...", flush=True)
    return fe.matrix(list(zip(df["resume_text"], df["jd_text"])), log_every=500)


def load_or_extract(splits: dict[str, pd.DataFrame], fe: FeatureExtractor):
    """Cache extracted features keyed by the dataset's mtime, so an
    interrupted run resumes without redoing ~4 minutes of extraction."""
    stamp = DATASET_PATH.stat().st_mtime
    if FEATURES_CACHE.exists():
        cached = np.load(FEATURES_CACHE)
        if cached["stamp"] == stamp:
            print("Using cached feature matrices.")
            return {k: cached[k] for k in splits}
    mats = {k: build_features(v, fe, k) for k, v in splits.items()}
    np.savez(FEATURES_CACHE, stamp=stamp, **mats)
    print(f"Feature matrices cached at {FEATURES_CACHE.name}")
    return mats


def label_accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return accuracy_score(
        [score_to_label(s) for s in y_true],
        [score_to_label(s) for s in np.clip(y_pred, 0, 100)],
    )


def importance_shares(model) -> dict[str, float]:
    imp = np.asarray(model.feature_importances_, dtype=float)
    imp = imp / imp.sum()
    return dict(zip(FEATURE_NAMES, imp))


def main() -> None:
    t0 = time.time()
    print("=== Stage 2: training ===")
    df = pd.read_csv(DATASET_PATH)
    train_df, val_df, test_df = split_dataset(df)
    print(f"Split sizes: train={len(train_df)} val={len(val_df)} test={len(test_df)}")

    fe = FeatureExtractor().fit(train_df["jd_text"].tolist())
    mats = load_or_extract({"train": train_df, "val": val_df, "test": test_df}, fe)
    X_train, X_val, X_test = mats["train"], mats["val"], mats["test"]
    y_train = train_df["score"].to_numpy()
    y_val = val_df["score"].to_numpy()
    y_test = test_df["score"].to_numpy()

    # -- three candidates --------------------------------------------------
    ridge = make_pipeline(StandardScaler(), Ridge(alpha=1.0))
    forest = RandomForestRegressor(n_estimators=300, random_state=SEED, n_jobs=-1)
    # CV clone of XGBoost uses a fixed budget (no eval set inside CV folds).
    xgb_cv = XGBRegressor(
        n_estimators=500, learning_rate=0.05, max_depth=5, subsample=0.9,
        colsample_bytree=0.9, random_state=SEED, n_jobs=-1, tree_method="hist",
    )

    print("\n5-fold CV on the training set (MAE, lower is better):")
    cv = KFold(n_splits=5, shuffle=True, random_state=SEED)
    cv_results = {}
    for name, model in [("Ridge", ridge), ("RandomForest", forest), ("XGBoost", xgb_cv)]:
        scores = -cross_val_score(
            model, X_train, y_train, cv=cv,
            scoring="neg_mean_absolute_error", n_jobs=-1,
        )
        cv_results[name] = (scores.mean(), scores.std())
        print(f"  {name:<13} MAE = {scores.mean():.3f} ± {scores.std():.3f}")

    # -- fit on train, compare on validation -------------------------------
    print("\nValidation comparison:")
    ridge.fit(X_train, y_train)
    forest.fit(X_train, y_train)
    xgb = XGBRegressor(
        n_estimators=2000, learning_rate=0.05, max_depth=5, subsample=0.9,
        colsample_bytree=0.9, random_state=SEED, n_jobs=-1, tree_method="hist",
        early_stopping_rounds=50, eval_metric="mae",
    )
    xgb.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=100)
    print(f"  XGBoost early stop at iteration {xgb.best_iteration}")

    val_maes = {}
    for name, model in [("Ridge", ridge), ("RandomForest", forest), ("XGBoost", xgb)]:
        val_maes[name] = mean_absolute_error(y_val, model.predict(X_val))
        print(f"  {name:<13} val MAE = {val_maes[name]:.3f}")

    best_tree = "XGBoost" if val_maes["XGBoost"] <= val_maes["RandomForest"] else "RandomForest"
    if val_maes["Ridge"] <= val_maes[best_tree]:
        print("  NOTE: the linear baseline beat the trees — saying so honestly.")
    print(f"\nBest tree model on validation: {best_tree} — tuning it.")

    # -- randomized search on the best tree model --------------------------
    if best_tree == "XGBoost":
        base = XGBRegressor(random_state=SEED, n_jobs=1, tree_method="hist")
        grid = {
            "n_estimators": [300, 500, 800, 1200],
            "learning_rate": [0.02, 0.03, 0.05, 0.08],
            "max_depth": [3, 4, 5, 6, 8],
            "subsample": [0.7, 0.8, 0.9, 1.0],
            "colsample_bytree": [0.6, 0.8, 1.0],
            "min_child_weight": [1, 3, 5, 10],
            "reg_lambda": [0.5, 1.0, 2.0, 5.0],
        }
    else:
        base = RandomForestRegressor(random_state=SEED, n_jobs=1)
        grid = {
            "n_estimators": [200, 300, 500, 800],
            "max_depth": [None, 8, 12, 16, 24],
            "min_samples_leaf": [1, 2, 4, 8],
            "max_features": [None, "sqrt", 0.5, 0.8],
        }
    search = RandomizedSearchCV(
        base, grid, n_iter=25, cv=5, scoring="neg_mean_absolute_error",
        random_state=SEED, n_jobs=-1, verbose=1,
    )
    search.fit(X_train, y_train)
    print(f"Best params: {search.best_params_}")
    print(f"Best CV MAE: {-search.best_score_:.3f}")

    tuned = search.best_estimator_
    tuned_val_mae = mean_absolute_error(y_val, tuned.predict(X_val))
    print(f"Tuned {best_tree} val MAE = {tuned_val_mae:.3f} "
          f"(untuned: {val_maes[best_tree]:.3f})")
    winner_name = best_tree
    winner = tuned if tuned_val_mae <= val_maes[best_tree] else \
        (xgb if best_tree == "XGBoost" else forest)

    # -- quality gates on the held-out test set ----------------------------
    y_pred = np.clip(winner.predict(X_test), 0, 100)
    r2 = r2_score(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)
    acc = label_accuracy(y_test, y_pred)
    shares = importance_shares(winner)
    max_share = max(shares.values())

    print("\n=== Quality gates (held-out test set) ===")
    print(f"  R2            = {r2:.4f}   (gate >= 0.85)  {'PASS' if r2 >= 0.85 else 'FAIL'}")
    print(f"  MAE           = {mae:.3f}    (gate <= 7.0)   {'PASS' if mae <= 7.0 else 'FAIL'}")
    print(f"  label acc     = {acc:.4f}   (gate >= 0.85)  {'PASS' if acc >= 0.85 else 'FAIL'}")
    print(f"  max feat imp  = {max_share:.3f}    (gate <= 0.60)  {'PASS' if max_share <= 0.60 else 'FAIL'}")
    print("  importance shares:", {k: round(v, 3) for k, v in shares.items()})

    if not (r2 >= 0.85 and mae <= 7.0 and acc >= 0.85 and max_share <= 0.60):
        raise SystemExit("Quality gates FAILED — tune and re-run (artifact NOT saved).")

    # -- bundle everything into one artifact -------------------------------
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    bundle = {
        "model": winner,
        "extractor": fe,
        "feature_names": FEATURE_NAMES,
        "winner": winner_name,
        "cv_results": cv_results,
        "val_maes": val_maes,
        "test_metrics": {"r2": r2, "mae": mae, "label_accuracy": acc},
        "importance_shares": shares,
        "seed": SEED,
    }
    joblib.dump(bundle, ARTIFACT_PATH, compress=3)
    size_mb = ARTIFACT_PATH.stat().st_size / 1e6
    print(f"\nSaved artifact: {ARTIFACT_PATH} ({size_mb:.2f} MB, gate < 50MB "
          f"{'PASS' if size_mb < 50 else 'FAIL'})")
    print(f"Total training time: {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
