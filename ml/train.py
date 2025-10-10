#!/usr/bin/env python3
"""
Logistic Regression training scaffold for CryptoRocket
- Builds features, creates labels with 24h lookahead, trains two LR models (LONG vs rest, SHORT vs rest)
- Performs temporal validation and probability calibration
- Exports artifacts consumable by Netlify Functions (Node) for inference

This is a scaffold: fill data sources for OHLCV/derivatives and texts as needed.
"""

import argparse
import json
import math
import os
import random
from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np


# ----------------------------
# Utility helpers
# ----------------------------

def set_seeds(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)


@dataclass
class PreprocessParams:
    feature_order: List[str]
    winsor_limits: Dict[str, Tuple[float, float]]
    imputer_values: Dict[str, float]
    scaler_mean: List[float]
    scaler_std: List[float]


def winsorize(values: np.ndarray, lower: float, upper: float) -> np.ndarray:
    return np.clip(values, lower, upper)


def zscore(values: np.ndarray, mean: np.ndarray, std: np.ndarray) -> np.ndarray:
    std_safe = np.where(std == 0, 1.0, std)
    return (values - mean) / std_safe


# ----------------------------
# Feature engineering (placeholder)
# ----------------------------

def build_features_placeholder(n: int, seed: int = 42) -> Tuple[np.ndarray, Dict[str, int]]:
    """Generate synthetic features to enable pipeline wiring.
    Replace with real feature builder.
    Returns X matrix and feature index mapping.
    """
    rng = np.random.default_rng(seed)
    feature_names = [
        "pct_1h",
        "pct_24h",
        "ret_log_24h",
        "vol_24h",
        "rsi_14",
        "volume_ratio_7d",
        "log_mcap",
        "sentiment_score_api",
        "funding_rate",
        "oi_change_24h",
    ]
    X = rng.normal(size=(n, len(feature_names)))
    idx = {name: i for i, name in enumerate(feature_names)}
    return X, idx


def make_labels_placeholder(n: int, seed: int = 42) -> Tuple[np.ndarray, np.ndarray]:
    """Create synthetic labels LONG/SHORT for demonstration."""
    rng = np.random.default_rng(seed)
    y_long = (rng.random(n) > 0.7).astype(int)
    y_short = (rng.random(n) > 0.75).astype(int)
    # ensure not both 1 simultaneously often
    both = (y_long == 1) & (y_short == 1)
    y_short[both] = 0
    return y_long, y_short


# ----------------------------
# Simple LR implementation for export (no sklearn dependency here)
# NOTE: For real training, use scikit-learn in a dedicated environment and then export
# ----------------------------

def sigmoid(z: np.ndarray) -> np.ndarray:
    return 1 / (1 + np.exp(-z))


def fit_logreg_l2_gd(X: np.ndarray, y: np.ndarray, l2: float = 1.0, lr: float = 0.1, epochs: int = 500) -> Tuple[np.ndarray, float]:
    """Very simple gradient descent logistic regression to produce weights for export.
    Not optimized; replace with sklearn in real pipeline.
    Returns (coef, intercept).
    """
    n, d = X.shape
    w = np.zeros(d)
    b = 0.0
    for _ in range(epochs):
        z = X @ w + b
        p = sigmoid(z)
        err = p - y
        grad_w = (X.T @ err) / n + l2 * w
        grad_b = np.mean(err)
        w -= lr * grad_w
        b -= lr * grad_b
    return w, b


def platt_calibration_params(p_raw: np.ndarray, y: np.ndarray) -> Tuple[float, float]:
    """Fit Platt scaling parameters by minimizing logloss via simple GD."""
    a, b = 1.0, 0.0
    lr = 0.1
    for _ in range(300):
        z = a * p_raw + b
        p = sigmoid(z)
        # gradients
        grad_a = np.mean((p - y) * p_raw)
        grad_b = np.mean(p - y)
        a -= lr * grad_a
        b -= lr * grad_b
    return float(a), float(b)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=20251010)
    parser.add_argument("--out", type=str, default=os.path.join("..", "artifacts", "model_artifacts.json"))
    parser.add_argument("--samples", type=int, default=5000)
    args = parser.parse_args()

    set_seeds(args.seed)

    # Build placeholder features/labels
    X, idx = build_features_placeholder(args.samples, seed=args.seed)
    y_long, y_short = make_labels_placeholder(args.samples, seed=args.seed + 1)

    # Winsorize (placeholder: clip to [-3, 3] for all features)
    X_clip = np.clip(X, -3.0, 3.0)

    # Impute (no NaNs here, real pipeline should compute medians)
    imputer_values = {name: 0.0 for name in idx.keys()}

    # Scale
    mean = X_clip.mean(axis=0)
    std = X_clip.std(axis=0)
    std[std == 0] = 1.0
    X_std = (X_clip - mean) / std

    # Train simple LR for LONG and SHORT
    wL, bL = fit_logreg_l2_gd(X_std, y_long, l2=1e-2, lr=0.2, epochs=800)
    wS, bS = fit_logreg_l2_gd(X_std, y_short, l2=1e-2, lr=0.2, epochs=800)

    # Raw probs and Platt calibration params (placeholder)
    pL_raw = sigmoid(X_std @ wL + bL)
    pS_raw = sigmoid(X_std @ wS + bS)
    aL, bL_platt = platt_calibration_params(pL_raw, y_long)
    aS, bS_platt = platt_calibration_params(pS_raw, y_short)

    # Thresholds (placeholder fixed, real pipeline should optimize by Sharpe)
    theta_long = 0.6
    theta_short = 0.6

    artifacts = {
        "version": "v1.0",
        "feature_order": list(idx.keys()),
        "winsor_limits": {name: [-3.0, 3.0] for name in idx.keys()},
        "imputer_values": imputer_values,
        "scaler_mean": mean.tolist(),
        "scaler_std": std.tolist(),
        "lr_long": {"coef": wL.tolist(), "intercept": float(bL), "calibration": {"type": "platt", "a": aL, "b": bL_platt}},
        "lr_short": {"coef": wS.tolist(), "intercept": float(bS), "calibration": {"type": "platt", "a": aS, "b": bS_platt}},
        "thresholds": {"theta_long": theta_long, "theta_short": theta_short},
        "vol_model": {"type": "realized_24h_rolling", "window_days": 14, "smoothing": 0.3},
        "kappa": 1.5,
        "seed": args.seed,
        "train_windows": [],
        "metrics": {}
    }

    out_path = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(artifacts, f)
    print(f"Exported artifacts to {out_path}")


if __name__ == "__main__":
    main()


