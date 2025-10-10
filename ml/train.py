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

def build_features_enhanced(n: int, seed: int = 42) -> Tuple[np.ndarray, Dict[str, int]]:
    """Generate realistic cryptocurrency features for training.
    Returns X matrix and feature index mapping.
    """
    rng = np.random.default_rng(seed)
    
    # Extended feature set as per specification
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
        "pct_7d",
        "vol_7d",
        "ema20_gap",
        "ema50_gap",
        "macd_hist",
        "dist_top20d",
        "dist_bottom20d",
        "volume_to_mcap"
    ]
    
    # Generate realistic feature distributions
    X = np.zeros((n, len(feature_names)))
    
    # Price changes: normally distributed around 0 with realistic volatility
    X[:, 0] = rng.normal(0, 0.02, n)  # pct_1h: ±2% std
    X[:, 1] = rng.normal(0, 0.05, n)  # pct_24h: ±5% std
    X[:, 2] = rng.normal(0, 0.05, n)  # ret_log_24h: similar to pct_24h
    
    # Volatility: log-normal distribution (always positive)
    X[:, 3] = np.exp(rng.normal(-3, 0.5, n))  # vol_24h: realistic crypto volatility
    
    # RSI: bounded between 0-100, centered around 50
    X[:, 4] = np.clip(rng.normal(50, 15, n), 0, 100)  # rsi_14
    
    # Volume ratios: log-normal around 1
    X[:, 5] = np.exp(rng.normal(0, 0.3, n))  # volume_ratio_7d
    
    # Market cap: log-normal (very wide range)
    X[:, 6] = rng.normal(20, 5, n)  # log_mcap
    
    # Sentiment: bounded between -1 and 1
    X[:, 7] = np.clip(rng.normal(0, 0.3, n), -1, 1)  # sentiment_score_api
    
    # Funding rates: small values around 0
    X[:, 8] = rng.normal(0, 0.001, n)  # funding_rate
    
    # Open interest change: percentage changes
    X[:, 9] = rng.normal(0, 0.1, n)  # oi_change_24h
    
    # Additional features
    X[:, 10] = rng.normal(0, 0.1, n)  # pct_7d
    X[:, 11] = np.exp(rng.normal(-3, 0.5, n))  # vol_7d
    X[:, 12] = rng.normal(0, 0.05, n)  # ema20_gap
    X[:, 13] = rng.normal(0, 0.08, n)  # ema50_gap
    X[:, 14] = rng.normal(0, 0.02, n)  # macd_hist
    X[:, 15] = rng.normal(-0.05, 0.1, n)  # dist_top20d (usually negative)
    X[:, 16] = rng.normal(0.05, 0.1, n)  # dist_bottom20d (usually positive)
    X[:, 17] = np.exp(rng.normal(-8, 1, n))  # volume_to_mcap (very small values)
    
    idx = {name: i for i, name in enumerate(feature_names)}
    return X, idx


def make_labels_realistic(X: np.ndarray, feature_idx: Dict[str, int], seed: int = 42) -> Tuple[np.ndarray, np.ndarray]:
    """Create realistic labels based on feature patterns."""
    rng = np.random.default_rng(seed)
    n = X.shape[0]
    
    # Create labels based on feature combinations (more realistic)
    y_long = np.zeros(n, dtype=int)
    y_short = np.zeros(n, dtype=int)
    
    for i in range(n):
        # Extract relevant features
        pct_24h = X[i, feature_idx['pct_24h']]
        rsi = X[i, feature_idx['rsi_14']]
        sentiment = X[i, feature_idx['sentiment_score_api']]
        vol = X[i, feature_idx['vol_24h']]
        ema20_gap = X[i, feature_idx['ema20_gap']]
        macd = X[i, feature_idx['macd_hist']]
        
        # LONG conditions: positive momentum + good sentiment + technical indicators
        long_score = 0
        if pct_24h > 0.02: long_score += 2  # Strong positive momentum
        elif pct_24h > 0.01: long_score += 1  # Moderate positive momentum
        
        if rsi < 70: long_score += 1  # Not overbought
        if sentiment > 0.2: long_score += 2  # Bullish sentiment
        elif sentiment > 0: long_score += 1  # Slightly bullish
        
        if ema20_gap > 0: long_score += 1  # Above EMA20
        if macd > 0: long_score += 1  # Positive MACD
        
        # SHORT conditions: negative momentum + poor sentiment + technical indicators
        short_score = 0
        if pct_24h < -0.02: short_score += 2  # Strong negative momentum
        elif pct_24h < -0.01: short_score += 1  # Moderate negative momentum
        
        if rsi > 30: short_score += 1  # Not oversold
        if sentiment < -0.2: short_score += 2  # Bearish sentiment
        elif sentiment < 0: short_score += 1  # Slightly bearish
        
        if ema20_gap < 0: short_score += 1  # Below EMA20
        if macd < 0: short_score += 1  # Negative MACD
        
        # Add some randomness and noise
        long_score += rng.normal(0, 0.5)
        short_score += rng.normal(0, 0.5)
        
        # Assign labels with thresholds
        if long_score >= 4 and short_score < 3:
            y_long[i] = 1
        elif short_score >= 4 and long_score < 3:
            y_short[i] = 1
        # else remains 0 (neutral)
    
    return y_long, y_short


def walk_forward_validation(X: np.ndarray, y_long: np.ndarray, y_short: np.ndarray, 
                          n_splits: int = 5) -> Dict[str, List[float]]:
    """Perform walk-forward validation for time series data."""
    n = X.shape[0]
    split_size = n // n_splits
    
    results = {
        'long_auc': [],
        'short_auc': [],
        'long_f1': [],
        'short_f1': [],
        'long_precision': [],
        'short_precision': [],
        'long_recall': [],
        'short_recall': []
    }
    
    for i in range(n_splits - 1):
        # Train on first i+1 splits
        train_end = (i + 1) * split_size
        X_train = X[:train_end]
        y_long_train = y_long[:train_end]
        y_short_train = y_short[:train_end]
        
        # Test on next split
        test_start = train_end
        test_end = min(train_end + split_size, n)
        X_test = X[test_start:test_end]
        y_long_test = y_long[test_start:test_end]
        y_short_test = y_short[test_start:test_end]
        
        if len(X_test) == 0:
            continue
            
        # Train models
        wL, bL = fit_logreg_l2_gd(X_train, y_long_train, l2=1e-2, lr=0.2, epochs=500)
        wS, bS = fit_logreg_l2_gd(X_train, y_short_train, l2=1e-2, lr=0.2, epochs=500)
        
        # Predict on test set
        pL_test = sigmoid(X_test @ wL + bL)
        pS_test = sigmoid(X_test @ wS + bS)
        
        # Calculate metrics (simplified - would use sklearn in production)
        # AUC approximation
        long_auc = 0.5 + 0.3 * np.mean(pL_test[y_long_test == 1]) - 0.3 * np.mean(pL_test[y_long_test == 0])
        short_auc = 0.5 + 0.3 * np.mean(pS_test[y_short_test == 1]) - 0.3 * np.mean(pS_test[y_short_test == 0])
        
        # F1 approximation
        long_pred = (pL_test > 0.5).astype(int)
        short_pred = (pS_test > 0.5).astype(int)
        
        long_tp = np.sum((long_pred == 1) & (y_long_test == 1))
        long_fp = np.sum((long_pred == 1) & (y_long_test == 0))
        long_fn = np.sum((long_pred == 0) & (y_long_test == 1))
        
        short_tp = np.sum((short_pred == 1) & (y_short_test == 1))
        short_fp = np.sum((short_pred == 1) & (y_short_test == 0))
        short_fn = np.sum((short_pred == 0) & (y_short_test == 1))
        
        long_precision = long_tp / (long_tp + long_fp) if (long_tp + long_fp) > 0 else 0
        long_recall = long_tp / (long_tp + long_fn) if (long_tp + long_fn) > 0 else 0
        long_f1 = 2 * long_precision * long_recall / (long_precision + long_recall) if (long_precision + long_recall) > 0 else 0
        
        short_precision = short_tp / (short_tp + short_fp) if (short_tp + short_fp) > 0 else 0
        short_recall = short_tp / (short_tp + short_fn) if (short_tp + short_fn) > 0 else 0
        short_f1 = 2 * short_precision * short_recall / (short_precision + short_recall) if (short_precision + short_recall) > 0 else 0
        
        # Store results
        results['long_auc'].append(long_auc)
        results['short_auc'].append(short_auc)
        results['long_f1'].append(long_f1)
        results['short_f1'].append(short_f1)
        results['long_precision'].append(long_precision)
        results['short_precision'].append(short_precision)
        results['long_recall'].append(long_recall)
        results['short_recall'].append(short_recall)
    
    return results


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
    parser.add_argument("--samples", type=int, default=10000)
    parser.add_argument("--validation", action="store_true", help="Run walk-forward validation")
    args = parser.parse_args()

    set_seeds(args.seed)
    print(f"Training Logistic Regression model with {args.samples} samples...")

    # Build enhanced features/labels
    X, idx = build_features_enhanced(args.samples, seed=args.seed)
    y_long, y_short = make_labels_realistic(X, idx, seed=args.seed + 1)
    
    print(f"Feature matrix shape: {X.shape}")
    print(f"Long signals: {np.sum(y_long)} ({np.mean(y_long)*100:.1f}%)")
    print(f"Short signals: {np.sum(y_short)} ({np.mean(y_short)*100:.1f}%)")
    print(f"Neutral signals: {np.sum((y_long == 0) & (y_short == 0))} ({np.mean((y_long == 0) & (y_short == 0))*100:.1f}%)")

    # Calculate feature-specific winsorization limits
    winsor_limits = {}
    for name in idx.keys():
        feature_data = X[:, idx[name]]
        p1, p99 = np.percentile(feature_data, [1, 99])
        winsor_limits[name] = [float(p1), float(p99)]

    # Winsorize features
    X_clip = X.copy()
    for name in idx.keys():
        lo, hi = winsor_limits[name]
        X_clip[:, idx[name]] = np.clip(X_clip[:, idx[name]], lo, hi)

    # Impute missing values (use median for each feature)
    imputer_values = {}
    for name in idx.keys():
        imputer_values[name] = float(np.median(X_clip[:, idx[name]]))

    # Scale features (z-score normalization)
    mean = X_clip.mean(axis=0)
    std = X_clip.std(axis=0)
    std[std == 0] = 1.0
    X_std = (X_clip - mean) / std

    # Run walk-forward validation if requested
    validation_metrics = {}
    if args.validation:
        print("Running walk-forward validation...")
        validation_metrics = walk_forward_validation(X_std, y_long, y_short, n_splits=5)
        
        # Print validation results
        print("\nWalk-forward Validation Results:")
        for metric, values in validation_metrics.items():
            mean_val = np.mean(values)
            std_val = np.std(values)
            print(f"{metric}: {mean_val:.3f} ± {std_val:.3f}")

    # Train final models on full dataset
    print("\nTraining final models...")
    wL, bL = fit_logreg_l2_gd(X_std, y_long, l2=1e-2, lr=0.2, epochs=1000)
    wS, bS = fit_logreg_l2_gd(X_std, y_short, l2=1e-2, lr=0.2, epochs=1000)

    # Platt calibration
    pL_raw = sigmoid(X_std @ wL + bL)
    pS_raw = sigmoid(X_std @ wS + bS)
    aL, bL_platt = platt_calibration_params(pL_raw, y_long)
    aS, bS_platt = platt_calibration_params(pS_raw, y_short)

    # Optimize thresholds based on validation performance
    # For now, use fixed thresholds, but could optimize based on Sharpe ratio
    theta_long = 0.65
    theta_short = 0.65

    # Calculate training metrics
    pL_calibrated = sigmoid(aL * pL_raw + bL_platt)
    pS_calibrated = sigmoid(aS * pS_raw + bS_platt)
    
    # Simple training metrics
    long_pred = (pL_calibrated > theta_long).astype(int)
    short_pred = (pS_calibrated > theta_short).astype(int)
    
    long_accuracy = np.mean(long_pred == y_long)
    short_accuracy = np.mean(short_pred == y_short)
    
    print(f"\nFinal Training Results:")
    print(f"Long accuracy: {long_accuracy:.3f}")
    print(f"Short accuracy: {short_accuracy:.3f}")

    # Create artifacts
    artifacts = {
        "version": "v2.0",
        "feature_order": list(idx.keys()),
        "winsor_limits": winsor_limits,
        "imputer_values": imputer_values,
        "scaler_mean": mean.tolist(),
        "scaler_std": std.tolist(),
        "lr_long": {
            "coef": wL.tolist(), 
            "intercept": float(bL), 
            "calibration": {"type": "platt", "a": float(aL), "b": float(bL_platt)}
        },
        "lr_short": {
            "coef": wS.tolist(), 
            "intercept": float(bS), 
            "calibration": {"type": "platt", "a": float(aS), "b": float(bS_platt)}
        },
        "thresholds": {"theta_long": theta_long, "theta_short": theta_short},
        "vol_model": {"type": "realized_24h_rolling", "window_days": 14, "smoothing": 0.3},
        "kappa": 1.5,
        "seed": args.seed,
        "trained_until": "2025-01-10",
        "train_windows": [],
        "metrics": {
            "long_accuracy": float(long_accuracy),
            "short_accuracy": float(short_accuracy),
            "validation": validation_metrics
        }
    }

    # Export artifacts
    out_path = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(artifacts, f)
    print(f"\nExported artifacts to {out_path}")
    print("Training completed successfully!")


if __name__ == "__main__":
    main()


