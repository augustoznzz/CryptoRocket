/*
  Netlify Function: /ai-sentiment/analyze
  - Accepts batch of texts, calls external AI API (placeholder), aggregates features
  - Caching by SHA-256 of text; fail-safe to zeros
*/

const crypto = require('crypto');

// Simple in-memory cache (clears on redeploy): hash -> { score, label, confidence, ts }
const CACHE = new Map();

function sha256(text) {
  return crypto.createHash('sha256').update(text, 'utf8').digest('hex');
}

function mockAiCallOne(text) {
  // Placeholder: map text length signals to sentiment
  const len = (text || '').length;
  const score = Math.tanh((len % 200) / 50 - 2); // [-1, 1]
  const label = score > 0.15 ? 'bullish' : score < -0.15 ? 'bearish' : 'neutral';
  const confidence = Math.min(1, Math.abs(score) + 0.2);
  return { text, sentiment_label: label, sentiment_score: score, rationale: 'mock', confidence };
}

async function analyzeTextsBatch(texts) {
  const out = [];
  for (const t of texts) {
    const key = sha256(t);
    if (CACHE.has(key)) {
      out.push({ ...CACHE.get(key), text: t, cached: true });
      continue;
    }
    // Replace with real API call using process.env.AI_API_KEY
    const res = mockAiCallOne(t);
    CACHE.set(key, res);
    out.push({ ...res, cached: false });
  }
  return out;
}

function aggregateFeatures(items) {
  if (!items || items.length === 0) {
    return {
      sentiment_score_api: 0,
      sentiment_confidence: 0,
      sentiment_count: 0,
      sentiment_std: 0,
      label_counts: { bullish: 0, neutral: 0, bearish: 0 }
    };
  }
  let wsum = 0, csum = 0, c2sum = 0;
  const labelCounts = { bullish: 0, neutral: 0, bearish: 0 };
  for (const it of items) {
    const w = Math.max(0, Math.min(1, it.confidence ?? 0));
    wsum += w;
    csum += w * (it.sentiment_score ?? 0);
    c2sum += w * Math.pow(it.sentiment_score ?? 0, 2);
    if (it.sentiment_label && labelCounts[it.sentiment_label] != null) labelCounts[it.sentiment_label] += 1;
  }
  const mean = wsum > 0 ? csum / wsum : 0;
  const varw = wsum > 0 ? Math.max(0, c2sum / wsum - mean * mean) : 0;
  const std = Math.sqrt(varw);
  const avgConf = items.reduce((a, b) => a + (b.confidence ?? 0), 0) / items.length;
  return {
    sentiment_score_api: mean,
    sentiment_confidence: Math.max(0, Math.min(1, avgConf)),
    sentiment_count: items.length,
    sentiment_std: std,
    label_counts: labelCounts
  };
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
    const body = event.body ? JSON.parse(event.body) : {};
    const texts = Array.isArray(body.texts) ? body.texts.slice(0, 128) : [];
    const window_hours = Number.isFinite(body.window_hours) ? body.window_hours : 24;
    if (texts.length === 0) {
      return { statusCode: 200, headers, body: JSON.stringify({ window_hours, features: aggregateFeatures([]), meta: { api_used: 'mock', cached_hits: 0, rate_limited: false } }) };
    }
    const analyzed = await analyzeTextsBatch(texts);
    const features = aggregateFeatures(analyzed);
    const cachedHits = analyzed.filter(x => x.cached).length;
    return { statusCode: 200, headers, body: JSON.stringify({ window_hours, features, meta: { api_used: 'mock', cached_hits: cachedHits, rate_limited: false } }) };
  } catch (e) {
    const features = aggregateFeatures([]);
    return { statusCode: 200, headers, body: JSON.stringify({ window_hours: 24, features, meta: { api_used: 'mock', error: e.message, fail_safe: true } }) };
  }
};


