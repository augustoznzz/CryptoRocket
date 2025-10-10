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

function analyzeTextSentiment(text) {
  // Enhanced sentiment analysis using keyword patterns and text analysis
  const lowerText = (text || '').toLowerCase();
  
  // Bullish keywords and phrases
  const bullishPatterns = [
    'bullish', 'bull run', 'moon', 'rocket', 'pump', 'surge', 'rally', 'breakout',
    'breakthrough', 'new high', 'ath', 'all time high', 'hodl', 'buy', 'long',
    'accumulate', 'institutional', 'adoption', 'mainstream', 'etf', 'approval',
    'partnership', 'upgrade', 'burn', 'deflationary', 'scarcity', 'halving',
    'positive', 'strong', 'support', 'resistance broken', 'momentum', 'trend'
  ];
  
  // Bearish keywords and phrases
  const bearishPatterns = [
    'bearish', 'bear market', 'crash', 'dump', 'sell', 'short', 'dip', 'correction',
    'pullback', 'resistance', 'rejection', 'weak', 'decline', 'fall', 'drop',
    'negative', 'concern', 'risk', 'volatile', 'uncertainty', 'fear', 'panic',
    'liquidate', 'margin call', 'fud', 'regulatory', 'ban', 'restriction',
    'hack', 'exploit', 'bug', 'vulnerability', 'loss', 'debt', 'default'
  ];
  
  // Calculate sentiment score based on keyword matches
  let bullishScore = 0;
  let bearishScore = 0;
  
  bullishPatterns.forEach(pattern => {
    const matches = (lowerText.match(new RegExp(pattern, 'g')) || []).length;
    bullishScore += matches * (pattern.length > 10 ? 1.5 : 1.0); // Weight longer phrases more
  });
  
  bearishPatterns.forEach(pattern => {
    const matches = (lowerText.match(new RegExp(pattern, 'g')) || []).length;
    bearishScore += matches * (pattern.length > 10 ? 1.5 : 1.0);
  });
  
  // Normalize scores
  const totalWords = lowerText.split(/\s+/).length;
  const normalizedBullish = Math.min(1, bullishScore / Math.max(1, totalWords * 0.1));
  const normalizedBearish = Math.min(1, bearishScore / Math.max(1, totalWords * 0.1));
  
  // Calculate final sentiment score [-1, 1]
  const rawScore = normalizedBullish - normalizedBearish;
  const sentimentScore = Math.tanh(rawScore * 3); // Scale and normalize
  
  // Determine label and confidence
  let sentimentLabel = 'neutral';
  let confidence = 0.5;
  
  if (sentimentScore > 0.2) {
    sentimentLabel = 'bullish';
    confidence = Math.min(0.95, 0.6 + Math.abs(sentimentScore) * 0.3);
  } else if (sentimentScore < -0.2) {
    sentimentLabel = 'bearish';
    confidence = Math.min(0.95, 0.6 + Math.abs(sentimentScore) * 0.3);
  } else {
    confidence = 0.4 + (0.2 - Math.abs(sentimentScore)) * 0.5;
  }
  
  // Generate rationale based on analysis
  let rationale = 'Neutral sentiment detected.';
  if (sentimentLabel === 'bullish') {
    rationale = `Bullish sentiment identified with ${bullishScore.toFixed(1)} positive signals.`;
  } else if (sentimentLabel === 'bearish') {
    rationale = `Bearish sentiment identified with ${bearishScore.toFixed(1)} negative signals.`;
  }
  
  return {
    text,
    sentiment_label: sentimentLabel,
    sentiment_score: sentimentScore,
    confidence: confidence,
    rationale: rationale
  };
}

async function callExternalAI(text) {
  // Placeholder for external AI API call (OpenAI, Anthropic, etc.)
  // In production, replace with actual API call using process.env.AI_API_KEY
  
  const apiKey = process.env.AI_API_KEY;
  if (!apiKey) {
    // Fallback to enhanced local analysis
    return analyzeTextSentiment(text);
  }
  
  try {
    // Example OpenAI API call (uncomment and modify as needed)
    /*
    const response = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        model: 'gpt-3.5-turbo',
        messages: [{
          role: 'system',
          content: 'Analyze the sentiment of cryptocurrency-related text. Respond with JSON: {"sentiment_label": "bullish/bearish/neutral", "sentiment_score": number, "confidence": number, "rationale": "explanation"}'
        }, {
          role: 'user',
          content: text
        }],
        temperature: 0.1,
        max_tokens: 150
      })
    });
    
    const data = await response.json();
    const result = JSON.parse(data.choices[0].message.content);
    return {
      text,
      sentiment_label: result.sentiment_label,
      sentiment_score: result.sentiment_score,
      confidence: result.confidence,
      rationale: result.rationale
    };
    */
    
    // For now, use enhanced local analysis
    return analyzeTextSentiment(text);
    
  } catch (error) {
    console.error('AI API call failed:', error);
    return analyzeTextSentiment(text);
  }
}

async function analyzeTextsBatch(texts) {
  const out = [];
  for (const t of texts) {
    const key = sha256(t);
    if (CACHE.has(key)) {
      out.push({ ...CACHE.get(key), text: t, cached: true });
      continue;
    }
    // Use enhanced AI analysis
    const res = await callExternalAI(t);
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


