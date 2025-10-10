# CryptoRocket ML System - Deployment Guide

## Overview

This guide covers the complete deployment and usage of the redesigned CryptoRocket system, which replaces the old rule-based approach with a Logistic Regression ML model and integrated AI sentiment analysis.

## System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Market Data   │    │  AI Sentiment    │    │   ML Model      │
│   (12h OHLCV)   │───▶│     Analysis     │───▶│   Inference     │
│                 │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                Feature Engineering & Preprocessing              │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Trading Signal Generation                    │
│              (LONG/SHORT/NEUTRAL with Confidence)               │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### 1. Enhanced Market Data Module (`market_data.py`)

- Fetches 12-hour OHLCV data from Binance API
- Calculates 18 technical indicators
- Includes fallback data generation for testing

### 2. AI Sentiment Analysis (`netlify/functions/ai-sentiment-analyze.js`)

- Enhanced keyword-based sentiment analysis
- Support for external AI API integration (OpenAI, Anthropic)
- Caching and rate limiting

### 3. ML Inference Engine (`netlify/functions/ml-infer.js`)

- Logistic Regression model inference
- Feature preprocessing and calibration
- Structured JSON output with absolute price changes

### 4. Training Pipeline (`ml/train.py`)

- Enhanced feature engineering
- Walk-forward validation
- Model calibration and export

### 5. Performance Evaluation (`performance_evaluation.py`)

- Comprehensive backtesting
- Risk metrics (Sharpe, Calmar, Sortino ratios)
- Visualization and reporting

## Installation

### Prerequisites

- Python 3.8+
- Node.js 16+
- Netlify CLI (for deployment)

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Install Node.js Dependencies

```bash
cd netlify/functions
npm install
```

### 3. Set Environment Variables

Create a `.env` file in the project root:

```bash
# AI API Configuration (optional)
AI_API_KEY=your_openai_or_anthropic_api_key

# Netlify Configuration
NETLIFY_SITE_ID=your_netlify_site_id
NETLIFY_ACCESS_TOKEN=your_netlify_access_token
```

## Usage

### 1. Train the ML Model

```bash
# Basic training
python ml/train.py --samples 10000 --out artifacts/model_artifacts.json

# With walk-forward validation
python ml/train.py --samples 10000 --validation --out artifacts/model_artifacts.json
```

### 2. Run Integrated Analysis

```bash
# Analyze top cryptocurrencies
python crypto_analyzer_integrated.py
```

### 3. Evaluate Performance

```bash
# Run performance evaluation and backtesting
python performance_evaluation.py
```

### 4. Local Development Server

```bash
# Start Netlify dev server
netlify dev

# Test endpoints
curl -X POST http://localhost:8888/.netlify/functions/ml-infer \
  -H "Content-Type: application/json" \
  -d '{"asset": "BTCUSDT", "texts": ["Bitcoin shows bullish momentum"]}'

curl -X POST http://localhost:8888/.netlify/functions/ai-sentiment-analyze \
  -H "Content-Type: application/json" \
  -d '{"texts": ["Bitcoin is mooning!", "Market crash incoming"]}'
```

## API Endpoints

### 1. ML Inference (`/ml-infer`)

**Input:**

```json
{
  "asset": "BTCUSDT",
  "texts": ["Bitcoin shows strong bullish momentum"],
  "use_sentiment": true
}
```

**Output:**

```json
{
  "asset": "BTCUSDT",
  "timestamp": "2025-01-10T12:00:00.000Z",
  "probabilities": {
    "long": 0.68,
    "short": 0.21,
    "neutral": 0.11
  },
  "signal": "LONG",
  "confidence": 0.68,
  "expected_return_range": {
    "low": -520.0,
    "median": 845.0,
    "high": 2535.0
  },
  "price_data_last_12h": {
    "open": 64300.0,
    "high": 65250.0,
    "low": 63800.0,
    "close": 65080.0
  },
  "price_change_absolute": {
    "1h": 125.5,
    "24h": 780.0
  },
  "ai_sentiment": {
    "score": 0.34,
    "label": "bullish",
    "confidence": 0.83
  },
  "model_info": {
    "type": "logistic_regression",
    "version": "v2.0",
    "trained_until": "2025-01-10"
  }
}
```

### 2. AI Sentiment Analysis (`/ai-sentiment-analyze`)

**Input:**

```json
{
  "texts": [
    "Bitcoin sees strong inflows from ETFs",
    "Market volatility remains high"
  ],
  "window_hours": 24
}
```

**Output:**

```json
{
  "window_hours": 24,
  "features": {
    "sentiment_score_api": 0.34,
    "sentiment_confidence": 0.83,
    "sentiment_count": 2,
    "sentiment_std": 0.12,
    "label_counts": {
      "bullish": 1,
      "neutral": 1,
      "bearish": 0
    }
  },
  "meta": {
    "api_used": "enhanced_local",
    "cached_hits": 0,
    "rate_limited": false
  }
}
```

## Feature Engineering

The system uses 18 features across multiple categories:

### Market Data Features

- `pct_1h`: 1-hour price change
- `pct_24h`: 24-hour price change
- `ret_log_24h`: Log returns over 24h
- `vol_24h`: Realized volatility
- `volume_ratio_7d`: Volume relative to 7-day average

### Technical Indicators

- `rsi_14`: 14-period RSI
- `ema20_gap`: Price distance from EMA20
- `ema50_gap`: Price distance from EMA50
- `macd_hist`: MACD histogram
- `dist_top20d`: Distance from 20-day high
- `dist_bottom20d`: Distance from 20-day low

### Market Fundamentals

- `log_mcap`: Log market capitalization
- `volume_to_mcap`: Volume to market cap ratio

### Sentiment Features

- `sentiment_score_api`: AI sentiment score (-1 to +1)
- `sentiment_confidence`: Confidence in sentiment analysis

### Derivatives (when available)

- `funding_rate`: Perpetual funding rate
- `oi_change_24h`: Open interest change

## Model Training

### Label Generation

- **LONG**: Future 24h return > +1.0%
- **SHORT**: Future 24h return < -1.0%
- **NEUTRAL**: All other cases

### Validation Strategy

- Time-based walk-forward validation
- 5-fold temporal splits
- No data leakage between train/test

### Performance Metrics

- ROC-AUC for each class
- F1-score for precision/recall balance
- Backtesting with Sharpe ratio optimization

## Deployment Options

### 1. Netlify Functions (Recommended)

```bash
# Deploy to Netlify
netlify deploy --prod
```

### 2. Local Python Server

```bash
# Run integrated analyzer
python crypto_analyzer_integrated.py
```

### 3. Docker Deployment

```dockerfile
FROM python:3.9-slim
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
CMD ["python", "crypto_analyzer_integrated.py"]
```

## Monitoring and Maintenance

### 1. Model Retraining

- Retrain weekly with new data
- Monitor performance degradation
- Update feature engineering as needed

### 2. Performance Monitoring

- Track prediction accuracy
- Monitor API response times
- Alert on system failures

### 3. Data Quality

- Validate market data feeds
- Check sentiment API reliability
- Monitor feature distributions

## Troubleshooting

### Common Issues

1. **Model artifacts not found**

   - Ensure `artifacts/model_artifacts.json` exists
   - Run training script first

2. **API rate limiting**

   - Implement proper caching
   - Use exponential backoff

3. **Poor prediction performance**
   - Check feature distributions
   - Retrain with more recent data
   - Adjust thresholds

### Debug Mode

```bash
# Enable verbose logging
python crypto_analyzer_integrated.py --verbose

# Test individual components
python -c "from market_data import MarketDataFetcher; print(MarketDataFetcher().get_target_cryptocurrencies())"
```

## Security Considerations

1. **API Keys**: Store in environment variables
2. **Rate Limiting**: Implement proper limits
3. **Input Validation**: Sanitize all inputs
4. **Error Handling**: Don't expose sensitive data

## Performance Optimization

1. **Caching**: Cache market data and sentiment results
2. **Parallel Processing**: Process multiple assets simultaneously
3. **Feature Caching**: Store computed features
4. **Model Optimization**: Use quantized models for faster inference

## Future Enhancements

1. **Deep Learning Models**: LSTM/Transformer architectures
2. **Multi-Asset Models**: Cross-asset correlation features
3. **Real-time Streaming**: WebSocket data feeds
4. **Advanced Sentiment**: News sentiment and social media analysis
5. **Risk Management**: Position sizing and portfolio optimization

## Support

For issues and questions:

1. Check the troubleshooting section
2. Review the performance evaluation output
3. Examine the model artifacts and metrics
4. Test individual components in isolation

## License

This project is licensed under the MIT License. See LICENSE file for details.
