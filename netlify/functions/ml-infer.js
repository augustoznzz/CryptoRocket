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

async function fetchMarketData(asset) {
  // Fetch 12-hour market data and calculate features
  try {
    // For production, this would call the market data service
    // For now, we'll use placeholder data that matches the expected format
    
    const basePrice = asset.includes('BTC') ? 65000 : 
                     asset.includes('ETH') ? 3500 : 
                     asset.includes('SOL') ? 180 : 100;
    
    // Generate realistic 12-hour OHLCV data
    const now = Date.now();
    const priceData = [];
    let currentPrice = basePrice;
    
    for (let i = 11; i >= 0; i--) {
      const timestamp = now - (i * 3600000); // 1 hour intervals
      const priceVariation = (Math.random() - 0.5) * 0.02; // ±1% variation
      currentPrice = currentPrice * (1 + priceVariation);
      
      const open = currentPrice;
      const close = currentPrice * (1 + (Math.random() - 0.5) * 0.01);
      const high = Math.max(open, close) * (1 + Math.random() * 0.005);
      const low = Math.min(open, close) * (1 - Math.random() * 0.005);
      const volume = 1000000 + Math.random() * 500000;
      
      priceData.push({
        timestamp,
        open,
        high,
        low,
        close,
        volume
      });
    }
    
    // Calculate features similar to the Python implementation
    const closes = priceData.map(p => p.close);
    const volumes = priceData.map(p => p.volume);
    const current = closes[closes.length - 1];
    
    // Basic price features
    const pct_1h = (closes[closes.length - 1] / closes[closes.length - 2] - 1) || 0;
    const pct_24h = (closes[closes.length - 1] / closes[0] - 1) || 0;
    const ret_log_24h = Math.log(closes[closes.length - 1] / closes[0]) || 0;
    
    // Simple volatility calculation
    const returns = [];
    for (let i = 1; i < closes.length; i++) {
      returns.push(Math.log(closes[i] / closes[i-1]));
    }
    const vol_24h = Math.sqrt(returns.reduce((sum, r) => sum + r*r, 0) / returns.length) || 0;
    
    // Simple RSI calculation
    let gains = 0, losses = 0;
    for (let i = 1; i < closes.length; i++) {
      const change = closes[i] - closes[i-1];
      if (change > 0) gains += change;
      else losses -= change;
    }
    const rsi_14 = losses === 0 ? 100 : 100 - (100 / (1 + gains / losses));
    
    // Simple EMA calculation
    const alpha = 2 / (20 + 1);
    let ema_20 = closes[0];
    for (let i = 1; i < closes.length; i++) {
      ema_20 = alpha * closes[i] + (1 - alpha) * ema_20;
    }
    
    const alpha_50 = 2 / (50 + 1);
    let ema_50 = closes[0];
    for (let i = 1; i < closes.length; i++) {
      ema_50 = alpha_50 * closes[i] + (1 - alpha_50) * ema_50;
    }
    
    // MACD histogram (simplified)
    const macd_hist = (ema_20 - ema_50) * 0.1;
    
    // Volume features
    const volume_24h = volumes.reduce((sum, v) => sum + v, 0);
    const volume_ratio_7d = 1.0; // Simplified
    
    // Price distance from EMAs
    const ema20_gap = (current / ema_20 - 1) || 0;
    const ema50_gap = (current / ema_50 - 1) || 0;
    
    // Distance from high/low
    const max_price = Math.max(...closes);
    const min_price = Math.min(...closes);
    const dist_top20d = (current / max_price - 1) || 0;
    const dist_bottom20d = (current / min_price - 1) || 0;
    
    // Market cap (simplified)
    const estimated_mcap = current * 21000000; // Rough BTC supply estimate
    const log_mcap = Math.log(estimated_mcap) || 0;
    const volume_to_mcap = volume_24h / estimated_mcap || 0;
    
    return {
      current_price: current,
      price_data_last_12h: {
        open: priceData[0].open,
        high: Math.max(...priceData.map(p => p.high)),
        low: Math.min(...priceData.map(p => p.low)),
        close: priceData[priceData.length - 1].close
      },
      features: {
        pct_1h,
        pct_24h,
        ret_log_24h,
        vol_24h,
        rsi_14,
        volume_ratio_7d,
        log_mcap,
        sentiment_score_api: 0.0, // Will be filled by sentiment API
        funding_rate: 0.0,
        oi_change_24h: 0.0,
        pct_7d: pct_24h * 7, // Simplified
        vol_7d: vol_24h, // Simplified
        ema20_gap,
        ema50_gap,
        macd_hist,
        dist_top20d,
        dist_bottom20d,
        volume_to_mcap
      }
    };
    
  } catch (error) {
    console.error('Error fetching market data:', error);
    return null;
  }
}

async function fetchSentimentData(texts) {
  // Fetch sentiment analysis for provided texts
  try {
    if (!texts || texts.length === 0) {
      return { sentiment_score_api: 0.0, sentiment_confidence: 0.0 };
    }
    
    // Call the sentiment analysis API
    const response = await fetch('/.netlify/functions/ai-sentiment-analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ texts })
    });
    
    if (!response.ok) {
      throw new Error(`Sentiment API error: ${response.status}`);
    }
    
    const sentimentData = await response.json();
    return sentimentData.features || { sentiment_score_api: 0.0, sentiment_confidence: 0.0 };
    
  } catch (error) {
    console.error('Error fetching sentiment data:', error);
    return { sentiment_score_api: 0.0, sentiment_confidence: 0.0 };
  }
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
      return { statusCode: 500, headers, body: JSON.stringify({ error: 'Model artifacts not found' }) };
    }

    const body = event.body ? JSON.parse(event.body) : {};
    const { asset = 'BTCUSDT', texts = [], use_sentiment = true } = body;

    // Fetch market data
    const marketData = await fetchMarketData(asset);
    if (!marketData) {
      return { statusCode: 500, headers, body: JSON.stringify({ error: 'Failed to fetch market data' }) };
    }

    // Fetch sentiment data if texts provided and sentiment enabled
    let sentimentFeatures = { sentiment_score_api: 0.0, sentiment_confidence: 0.0 };
    if (use_sentiment && texts.length > 0) {
      sentimentFeatures = await fetchSentimentData(texts);
    }

    // Merge market features with sentiment features
    const allFeatures = { ...marketData.features, ...sentimentFeatures };

    // Build feature vector in artifact order
    const order = artifacts.feature_order;
    const xRaw = order.map((name) => {
      const v = allFeatures[name];
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

    // Calculate expected return range based on volatility and confidence
    const volExp = marketData.features.vol_24h || 0.045; // Use actual volatility or fallback
    const pnlRange = estimatePotential(pL, pS, volExp, artifacts.kappa || 1.5);

    // Calculate absolute price changes (no percentage symbols)
    const currentPrice = marketData.current_price;
    const priceChange1h = currentPrice * marketData.features.pct_1h;
    const priceChange24h = currentPrice * marketData.features.pct_24h;

    const nowISO = new Date().toISOString();
    
    // Format expected return range as absolute values
    const expectedReturnRange = {
      low: currentPrice * (pnlRange.p10 / 100),
      median: currentPrice * (pnlRange.p50 / 100),
      high: currentPrice * (pnlRange.p90 / 100)
    };

    const response = {
      asset,
      timestamp: nowISO,
      probabilities: { 
        long: Math.round(pL * 1000) / 1000, 
        short: Math.round(pS * 1000) / 1000, 
        neutral: Math.round(pN * 1000) / 1000 
      },
      signal,
      confidence: Math.round(Math.max(pL, pS) * 1000) / 1000,
      expected_return_range: expectedReturnRange,
      price_data_last_12h: marketData.price_data_last_12h,
      price_change_absolute: {
        "1h": Math.round(priceChange1h * 100) / 100,
        "24h": Math.round(priceChange24h * 100) / 100
      },
      ai_sentiment: {
        score: Math.round(sentimentFeatures.sentiment_score_api * 1000) / 1000,
        label: sentimentFeatures.sentiment_score_api > 0.2 ? 'bullish' : 
               sentimentFeatures.sentiment_score_api < -0.2 ? 'bearish' : 'neutral',
        confidence: Math.round(sentimentFeatures.sentiment_confidence * 1000) / 1000
      },
      model_info: {
        type: 'logistic_regression',
        version: artifacts.version || 'v1.0',
        trained_until: artifacts.trained_until || '2025-01-10'
      }
    };

    return { statusCode: 200, headers, body: JSON.stringify(response) };
  } catch (e) {
    console.error('ML inference error:', e);
    return { statusCode: 500, headers, body: JSON.stringify({ error: e.message }) };
  }
};


