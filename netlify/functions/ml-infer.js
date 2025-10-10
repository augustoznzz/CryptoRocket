/*
  Netlify Function: ML Inference for CryptoRocket
  - Loads exported logistic regression artifacts (JSON)
  - Builds feature vector from market + optional sentiment inputs
  - Applies preprocessing, LR logits, calibration, and thresholding
  - Returns probabilities, signal, confidence, potential range
*/

const fs = require('fs');
const path = require('path');

// Lazy-loaded artifacts
let ARTIFACTS = null;

function loadArtifactsOnce() {
  if (ARTIFACTS) return ARTIFACTS;
  try {
    // Look for artifacts in repo path ../artifacts/model_artifacts.json relative to this file
    const artifactsPath = path.resolve(__dirname, '../../artifacts/model_artifacts.json');
    const data = fs.readFileSync(artifactsPath, 'utf8');
    ARTIFACTS = JSON.parse(data);
    return ARTIFACTS;
  } catch (e) {
    console.error('Failed to load model artifacts:', e.message);
    ARTIFACTS = null;
    return null;
  }
}

function sigmoid(z) {
  return 1 / (1 + Math.exp(-z));
}

function applyCalibration(p, calib) {
  if (!calib || !calib.type) return p;
  if (calib.type === 'platt') {
    const z = calib.a * p + calib.b;
    return Math.min(1, Math.max(0, sigmoid(z)));
  }
  // Fallback
  return p;
}

function dot(a, b) {
  let s = 0;
  for (let i = 0; i < a.length; i++) s += a[i] * b[i];
  return s;
}

function winsorClip(x, limits, featureOrder) {
  const out = x.slice();
  for (let i = 0; i < featureOrder.length; i++) {
    const name = featureOrder[i];
    const lim = limits[name];
    if (!lim) continue;
    const lo = lim[0];
    const hi = lim[1];
    out[i] = Math.max(lo, Math.min(hi, out[i]));
  }
  return out;
}

function impute(x, imputerValues, featureOrder) {
  const out = x.slice();
  const missingFlags = {};
  for (let i = 0; i < featureOrder.length; i++) {
    const name = featureOrder[i];
    if (out[i] == null || Number.isNaN(out[i])) {
      out[i] = imputerValues[name] ?? 0;
      missingFlags[`is_missing_${name}`] = 1;
    } else {
      missingFlags[`is_missing_${name}`] = 0;
    }
  }
  return { x: out, missingFlags };
}

function zscore(x, mean, std) {
  return x.map((v, i) => {
    const s = std[i] === 0 ? 1 : std[i];
    return (v - mean[i]) / s;
  });
}

function decideSignal(pL, pS, thresholds) {
  const { theta_long: tL, theta_short: tS } = thresholds;
  const longHit = pL >= tL;
  const shortHit = pS >= tS;
  if (longHit && !shortHit) return 'LONG';
  if (shortHit && !longHit) return 'SHORT';
  if (longHit && shortHit) return pL >= pS ? 'LONG' : 'SHORT';
  return 'NEUTRAL';
}

function estimatePotential(pL, pS, volExp, kappa) {
  const pStrong = Math.max(pL, pS);
  const abs = kappa * pStrong * volExp * 100; // convert to %
  // crude symmetric range for scaffold; real impl should bootstrap
  return {
    p10: -Math.round(abs * 0.6 * 10) / 10,
    p50: Math.round((pL > pS ? +abs * 0.3 : -abs * 0.3) * 10) / 10,
    p90: Math.round(abs * 1.2 * 10) / 10
  };
}

async function fetchMarketSnapshot(asset) {
  // Scaffold: use existing analyze endpoint raw logic is heavy; here accept direct inputs
  // In real deployment, query a market data service or reuse CoinGecko.
  return null;
}

exports.handler = async (event) => {
  const headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS'
  };
  if (event.httpMethod === 'OPTIONS') {
    return { statusCode: 200, headers, body: '' };
  }

  try {
    const artifacts = loadArtifactsOnce();
    if (!artifacts) {
      return { statusCode: 500, headers, body: JSON.stringify({ error: 'Artifacts not found' }) };
    }

    const body = event.body ? JSON.parse(event.body) : {};
    const { asset = 'BTCUSDT', features = {}, use_sentiment = true } = body;

    // Build feature vector in artifact order; expect client to pass snapshot values
    const order = artifacts.feature_order;
    const xRaw = order.map((name) => {
      const v = features[name];
      return typeof v === 'number' ? v : null;
    });

    // Preprocess
    const xClip = winsorClip(xRaw, artifacts.winsor_limits, order);
    const imp = impute(xClip, artifacts.imputer_values, order);
    const xStd = zscore(imp.x, artifacts.scaler_mean, artifacts.scaler_std);

    // LONG head
    const zL = dot(artifacts.lr_long.coef, xStd) + artifacts.lr_long.intercept;
    const pLraw = sigmoid(zL);
    const pL = applyCalibration(pLraw, artifacts.lr_long.calibration);

    // SHORT head
    const zS = dot(artifacts.lr_short.coef, xStd) + artifacts.lr_short.intercept;
    const pSraw = sigmoid(zS);
    const pS = applyCalibration(pSraw, artifacts.lr_short.calibration);

    const pN = Math.max(0, 1 - Math.min(1, pL + pS));
    const signal = decideSignal(pL, pS, artifacts.thresholds);

    // Volatility expectation: simple placeholder 4.5% daily
    const volExp = 0.045;
    const pnlRange = estimatePotential(pL, pS, volExp, artifacts.kappa || 1.5);

    const nowISO = new Date().toISOString();
    const response = {
      asset,
      timestamp: nowISO,
      probabilities: { long: pL, short: pS, neutral: pN },
      signal,
      confidence: Math.max(pL, pS),
      expected_pnl_range_pct_24h: pnlRange,
      features_snapshot: features,
      model_info: { type: 'logistic_regression', version: artifacts.version, calibrated: !!artifacts.lr_long.calibration }
    };

    return { statusCode: 200, headers, body: JSON.stringify(response) };
  } catch (e) {
    return { statusCode: 500, headers, body: JSON.stringify({ error: e.message }) };
  }
};


