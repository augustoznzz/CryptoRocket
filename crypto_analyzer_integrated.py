#!/usr/bin/env python3
"""
Integrated CryptoRocket Analysis System
Combines market data, sentiment analysis, and ML inference into a unified system
"""

import json
import time
import requests
from datetime import datetime
from typing import Dict, List, Optional
import numpy as np
from market_data import MarketDataFetcher, TechnicalIndicators

class CryptoAnalyzer:
    """Integrated cryptocurrency analysis system"""
    
    def __init__(self, verbose: bool = True):
        """Initialize the crypto analyzer"""
        self.verbose = verbose
        self.market_fetcher = MarketDataFetcher(verbose=verbose)
        self.base_url = "http://localhost:8888"  # Local Netlify dev server
        self.cache = {}
        self.cache_timeout = 300  # 5 minutes
        
    def log(self, message: str):
        """Log message if verbose mode is enabled"""
        if self.verbose:
            print(f"[CRYPTO-ANALYZER] {message}")
    
    def fetch_sentiment_analysis(self, texts: List[str]) -> Dict:
        """Fetch sentiment analysis for given texts"""
        try:
            if not texts:
                return {"sentiment_score_api": 0.0, "sentiment_confidence": 0.0}
            
            # For local development, use mock sentiment data
            # In production, this would call the Netlify function
            return self._mock_sentiment_analysis(texts)
            
        except Exception as e:
            self.log(f"Error fetching sentiment analysis: {str(e)}")
            return {"sentiment_score_api": 0.0, "sentiment_confidence": 0.0}
    
    def _mock_sentiment_analysis(self, texts: List[str]) -> Dict:
        """Mock sentiment analysis for local development"""
        # Simple sentiment analysis based on keywords
        bullish_keywords = ['bull', 'moon', 'pump', 'surge', 'rally', 'buy', 'long', 'hodl']
        bearish_keywords = ['bear', 'crash', 'dump', 'sell', 'short', 'fud', 'panic', 'drop']
        
        total_score = 0.0
        total_confidence = 0.0
        
        for text in texts:
            text_lower = text.lower()
            bullish_count = sum(1 for word in bullish_keywords if word in text_lower)
            bearish_count = sum(1 for word in bearish_keywords if word in text_lower)
            
            # Calculate sentiment score
            score = (bullish_count - bearish_count) / max(1, len(text.split()))
            score = np.clip(score, -1, 1)
            
            # Calculate confidence based on keyword density
            confidence = min(0.9, (bullish_count + bearish_count) / max(1, len(text.split())) + 0.3)
            
            total_score += score
            total_confidence += confidence
        
        avg_score = total_score / len(texts) if texts else 0.0
        avg_confidence = total_confidence / len(texts) if texts else 0.0
        
        return {
            "sentiment_score_api": avg_score,
            "sentiment_confidence": avg_confidence
        }
    
    def analyze_cryptocurrency(self, symbol: str, sentiment_texts: List[str] = None) -> Dict:
        """Analyze a single cryptocurrency with market data and sentiment"""
        try:
            self.log(f"Analyzing {symbol}...")
            
            # Fetch market data
            market_data = self.market_fetcher.get_12h_ohlcv_data(f"{symbol}USDT")
            if not market_data:
                raise ValueError(f"Failed to fetch market data for {symbol}")
            
            # Calculate features
            features = self.market_fetcher.calculate_features(market_data)
            
            # Fetch sentiment analysis if texts provided
            sentiment_features = {"sentiment_score_api": 0.0, "sentiment_confidence": 0.0}
            if sentiment_texts:
                sentiment_features = self.fetch_sentiment_analysis(sentiment_texts)
                features.update(sentiment_features)
            
            # Mock ML inference (in production, this would call the Netlify function)
            ml_result = self._mock_ml_inference(features)
            
            # Combine all data
            analysis_result = {
                "asset": symbol,
                "timestamp": datetime.now().isoformat(),
                "current_price": market_data['current_price'],
                "price_data_last_12h": {
                    "open": market_data['open'][0] if market_data['open'] else 0,
                    "high": max(market_data['high']) if market_data['high'] else 0,
                    "low": min(market_data['low']) if market_data['low'] else 0,
                    "close": market_data['close'][-1] if market_data['close'] else 0
                },
                "price_change_absolute": {
                    "1h": market_data['current_price'] * features.get('pct_1h', 0),
                    "24h": market_data['current_price'] * features.get('pct_24h', 0)
                },
                "technical_indicators": {
                    "rsi_14": features.get('rsi_14', 50),
                    "volatility_24h": features.get('vol_24h', 0),
                    "volume_24h": sum(market_data.get('volume', [0])),
                    "ema20_gap": features.get('ema20_gap', 0),
                    "ema50_gap": features.get('ema50_gap', 0),
                    "macd_histogram": features.get('macd_hist', 0)
                },
                "ai_sentiment": {
                    "score": sentiment_features.get('sentiment_score_api', 0.0),
                    "label": self._get_sentiment_label(sentiment_features.get('sentiment_score_api', 0.0)),
                    "confidence": sentiment_features.get('sentiment_confidence', 0.0)
                },
                "ml_prediction": ml_result,
                "features_used": features
            }
            
            self.log(f"Analysis completed for {symbol}")
            return analysis_result
            
        except Exception as e:
            self.log(f"Error analyzing {symbol}: {str(e)}")
            return {"error": str(e), "asset": symbol}
    
    def _mock_ml_inference(self, features: Dict) -> Dict:
        """Mock ML inference for local development"""
        # Simple rule-based prediction based on features
        pct_24h = features.get('pct_24h', 0)
        rsi = features.get('rsi_14', 50)
        sentiment = features.get('sentiment_score_api', 0)
        vol = features.get('vol_24h', 0)
        
        # Calculate probabilities based on feature combinations
        long_score = 0.0
        short_score = 0.0
        
        # LONG factors
        if pct_24h > 0.02: long_score += 0.3
        elif pct_24h > 0.01: long_score += 0.2
        if rsi < 70: long_score += 0.1
        if sentiment > 0.2: long_score += 0.3
        elif sentiment > 0: long_score += 0.1
        if vol > 0.05: long_score += 0.1  # High volatility can be bullish
        
        # SHORT factors
        if pct_24h < -0.02: short_score += 0.3
        elif pct_24h < -0.01: short_score += 0.2
        if rsi > 30: short_score += 0.1
        if sentiment < -0.2: short_score += 0.3
        elif sentiment < 0: short_score += 0.1
        if vol > 0.05: short_score += 0.1  # High volatility can be bearish
        
        # Add some randomness
        long_score += np.random.normal(0, 0.05)
        short_score += np.random.normal(0, 0.05)
        
        # Normalize probabilities
        total_score = long_score + short_score + 0.5  # Base neutral probability
        prob_long = max(0, min(1, long_score / total_score))
        prob_short = max(0, min(1, short_score / total_score))
        prob_neutral = max(0, 1 - prob_long - prob_short)
        
        # Normalize to sum to 1
        total_prob = prob_long + prob_short + prob_neutral
        prob_long /= total_prob
        prob_short /= total_prob
        prob_neutral /= total_prob
        
        # Determine signal
        signal = "NEUTRAL"
        if prob_long >= 0.6: signal = "LONG"
        elif prob_short >= 0.6: signal = "SHORT"
        
        # Calculate expected return range (simplified)
        current_price = 65000  # Mock current price
        vol_exp = vol if vol > 0 else 0.05
        expected_return = {
            "low": current_price * -vol_exp * 0.8,
            "median": current_price * vol_exp * (0.3 if signal == "LONG" else -0.3),
            "high": current_price * vol_exp * 1.2
        }
        
        return {
            "probabilities": {
                "long": round(prob_long, 3),
                "short": round(prob_short, 3),
                "neutral": round(prob_neutral, 3)
            },
            "signal": signal,
            "confidence": round(max(prob_long, prob_short), 3),
            "expected_return_range": expected_return
        }
    
    def _get_sentiment_label(self, score: float) -> str:
        """Convert sentiment score to label"""
        if score > 0.2:
            return "bullish"
        elif score < -0.2:
            return "bearish"
        else:
            return "neutral"
    
    def analyze_multiple_cryptocurrencies(self, symbols: List[str], 
                                        sentiment_texts: List[str] = None) -> List[Dict]:
        """Analyze multiple cryptocurrencies"""
        results = []
        
        for symbol in symbols:
            try:
                result = self.analyze_cryptocurrency(symbol, sentiment_texts)
                results.append(result)
                
                # Add delay to avoid rate limiting
                time.sleep(0.1)
                
            except Exception as e:
                self.log(f"Error analyzing {symbol}: {str(e)}")
                results.append({"error": str(e), "asset": symbol})
        
        return results
    
    def get_top_cryptocurrencies(self, limit: int = 10) -> List[Dict]:
        """Get analysis for top cryptocurrencies"""
        # Top cryptocurrencies by market cap
        top_symbols = [
            'BTC', 'ETH', 'BNB', 'SOL', 'XRP', 'ADA', 'DOGE', 'TRX', 'LINK', 'DOT'
        ]
        
        # Sample sentiment texts for demonstration
        sample_texts = [
            "Bitcoin shows strong bullish momentum with institutional adoption increasing",
            "Ethereum network upgrades continue to drive positive sentiment",
            "Market volatility remains high with mixed signals across altcoins",
            "Regulatory clarity is improving investor confidence in crypto markets"
        ]
        
        return self.analyze_multiple_cryptocurrencies(
            top_symbols[:limit], 
            sample_texts
        )

def main():
    """Main function to demonstrate the integrated system"""
    print("🚀 CryptoRocket Integrated Analysis System")
    print("=" * 50)
    
    # Initialize analyzer
    analyzer = CryptoAnalyzer(verbose=True)
    
    # Analyze top cryptocurrencies
    print("\n📊 Analyzing top cryptocurrencies...")
    results = analyzer.get_top_cryptocurrencies(limit=5)
    
    # Display results
    print("\n📈 Analysis Results:")
    print("-" * 80)
    
    for result in results:
        if "error" in result:
            print(f"❌ {result['asset']}: {result['error']}")
            continue
            
        asset = result['asset']
        price = result['current_price']
        signal = result['ml_prediction']['signal']
        confidence = result['ml_prediment']['confidence']
        sentiment = result['ai_sentiment']['label']
        
        print(f"\n🔸 {asset}")
        print(f"   Price: ${price:,.2f}")
        print(f"   Signal: {signal} (Confidence: {confidence:.1%})")
        print(f"   Sentiment: {sentiment}")
        
        # Price changes (absolute values, no % symbols)
        price_1h = result['price_change_absolute']['1h']
        price_24h = result['price_change_absolute']['24h']
        
        print(f"   1h Change: ${price_1h:+.2f}")
        print(f"   24h Change: ${price_24h:+.2f}")
        
        # Technical indicators
        tech = result['technical_indicators']
        print(f"   RSI: {tech['rsi_14']:.1f}")
        print(f"   Volatility: {tech['volatility_24h']:.3f}")
    
    print("\n✅ Analysis completed!")
    
    # Save results to file
    output_file = f"crypto_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"📁 Results saved to: {output_file}")

if __name__ == "__main__":
    main()
