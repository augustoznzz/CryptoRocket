#!/usr/bin/env python3
"""
Integrated CryptoRocket Analysis System
Combines market data, sentiment analysis, and ML inference into a unified system
"""

import json
import time
import urllib.request
import urllib.parse
from datetime import datetime
from typing import Dict, List, Optional
import random

# Try to import optional dependencies
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    print("Note: numpy not available, using fallback calculations")

try:
    from market_data import MarketDataFetcher, TechnicalIndicators
    MARKET_DATA_AVAILABLE = True
except ImportError:
    MARKET_DATA_AVAILABLE = False
    print("Note: market_data module not available, using simplified data fetching")

class CryptoAnalyzer:
    """Integrated cryptocurrency analysis system"""
    
    def __init__(self, verbose: bool = True):
        """Initialize the crypto analyzer"""
        self.verbose = verbose
        self.base_url = "http://localhost:8888"  # Local Netlify dev server
        self.cache = {}
        self.cache_timeout = 300  # 5 minutes
        
        # Initialize market data fetcher if available
        if MARKET_DATA_AVAILABLE:
            self.market_fetcher = MarketDataFetcher(verbose=verbose)
        else:
            self.market_fetcher = None
        
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
    
    def _fetch_real_price_simple(self, symbol: str) -> Dict:
        """Fetch real price using only standard library"""
        try:
            # Map symbols to CoinGecko IDs
            symbol_map = {
                'BTC': 'bitcoin',
                'ETH': 'ethereum',
                'BNB': 'binancecoin',
                'SOL': 'solana',
                'ADA': 'cardano',
                'XRP': 'ripple',
                'DOGE': 'dogecoin',
                'TRX': 'tron',
                'LINK': 'chainlink',
                'DOT': 'polkadot'
            }
            
            coin_id = symbol_map.get(symbol.upper(), 'bitcoin')
            
            # Use CoinGecko API
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd&include_24hr_change=true&include_24hr_vol=true"
            
            with urllib.request.urlopen(url, timeout=10) as response:
                data = json.loads(response.read().decode())
            
            if coin_id in data:
                coin_data = data[coin_id]
                current_price = coin_data.get('usd', 0)
                change_24h_pct = coin_data.get('usd_24h_change', 0)
                volume_24h = coin_data.get('usd_24h_vol', 1000000000)
                
                # Generate realistic OHLCV data based on real price
                closes = []
                volumes = []
                
                for i in range(24):
                    # Simulate hourly price movement based on 24h change
                    hourly_change = change_24h_pct / 24 + random.uniform(-abs(change_24h_pct) * 0.1, abs(change_24h_pct) * 0.1)
                    price = current_price * (1 - change_24h_pct * (23 - i) / 24 / 100)
                    volume = volume_24h / 24 * (1 + random.uniform(-0.2, 0.2))
                    
                    closes.append(price)
                    volumes.append(volume)
                
                return {
                    'timestamps': [int(time.time() * 1000) - (23-i) * 3600000 for i in range(24)],
                    'open': [closes[0]] * 24,  # Simplified
                    'high': [p * (1 + abs(random.uniform(0, 0.01))) for p in closes],
                    'low': [p * (1 - abs(random.uniform(0, 0.01))) for p in closes],
                    'close': closes,
                    'volume': volumes,
                    'current_price': current_price,
                    'source': 'CoinGecko API'
                }
            
        except Exception as e:
            self.log(f"Failed to fetch real data for {symbol}: {e}")
            return None
    
    def _calculate_features_simple(self, market_data: Dict) -> Dict[str, float]:
        """Calculate features without numpy dependency"""
        closes = market_data['close']
        volumes = market_data['volume']
        current_price = market_data['current_price']
        
        if not closes or len(closes) < 2:
            return self._get_default_features_simple()
        
        # Basic price features
        price_1h = (closes[-1] / closes[-2] - 1) if len(closes) >= 2 else 0
        price_24h = (closes[-1] / closes[0] - 1) if len(closes) >= 24 else (closes[-1] / closes[0] - 1) if len(closes) > 0 else 0
        
        # Simple volatility calculation
        returns = []
        for i in range(1, len(closes)):
            if closes[i-1] > 0:
                returns.append((closes[i] - closes[i-1]) / closes[i-1])
        
        if returns:
            mean_return = sum(returns) / len(returns)
            variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
            vol_24h = variance ** 0.5 if variance > 0 else 0
        else:
            vol_24h = 0
        
        # Simple RSI calculation
        gains = []
        losses = []
        for i in range(1, min(len(closes), 15)):
            change = closes[i] - closes[i-1]
            if change > 0:
                gains.append(change)
            else:
                losses.append(-change)
        
        if gains and losses:
            avg_gain = sum(gains) / len(gains)
            avg_loss = sum(losses) / len(losses)
            rsi_14 = 100 - (100 / (1 + avg_gain / avg_loss)) if avg_loss > 0 else 100
        else:
            rsi_14 = 50
        
        # Simple EMA calculation
        def calculate_ema(prices, period):
            if len(prices) < period:
                return prices[-1] if prices else 0
            alpha = 2 / (period + 1)
            ema = prices[0]
            for price in prices[1:]:
                ema = alpha * price + (1 - alpha) * ema
            return ema
        
        ema_20 = calculate_ema(closes, 20)
        ema_50 = calculate_ema(closes, 50)
        
        # MACD histogram (simplified)
        macd_hist = (ema_20 - ema_50) * 0.1
        
        # Volume features
        volume_24h = sum(volumes) if volumes else 0
        volume_ratio_7d = 1.0  # Simplified
        
        # Price distance from EMAs
        ema20_gap = (current_price / ema_20 - 1) if ema_20 > 0 else 0
        ema50_gap = (current_price / ema_50 - 1) if ema_50 > 0 else 0
        
        # Distance from high/low
        max_price = max(closes) if closes else current_price
        min_price = min(closes) if closes else current_price
        dist_top20d = (current_price / max_price - 1) if max_price > 0 else 0
        dist_bottom20d = (current_price / min_price - 1) if min_price > 0 else 0
        
        # Market cap (simplified)
        estimated_mcap = current_price * 21000000  # Rough BTC supply estimate
        log_mcap = __import__('math').log(estimated_mcap) if estimated_mcap > 0 else 0
        volume_to_mcap = volume_24h / estimated_mcap if estimated_mcap > 0 else 0
        
        return {
            'pct_1h': price_1h,
            'pct_24h': price_24h,
            'ret_log_24h': price_24h * 0.8,  # Simplified log return
            'vol_24h': vol_24h,
            'rsi_14': rsi_14,
            'volume_ratio_7d': volume_ratio_7d,
            'log_mcap': log_mcap,
            'sentiment_score_api': 0.0,  # Will be filled by sentiment API
            'funding_rate': 0.0,  # Would need derivatives data
            'oi_change_24h': 0.0,  # Would need derivatives data
            'pct_7d': price_24h * 7,  # Simplified
            'vol_7d': vol_24h,  # Simplified
            'ema20_gap': ema20_gap,
            'ema50_gap': ema50_gap,
            'macd_hist': macd_hist,
            'dist_top20d': dist_top20d,
            'dist_bottom20d': dist_bottom20d,
            'volume_to_mcap': volume_to_mcap
        }
    
    def _get_default_features_simple(self) -> Dict[str, float]:
        """Return default feature values when data is unavailable"""
        return {
            'pct_1h': 0.0, 'pct_24h': 0.0, 'ret_log_24h': 0.0, 'vol_24h': 0.0,
            'rsi_14': 50.0, 'volume_ratio_7d': 1.0, 'log_mcap': 0.0,
            'sentiment_score_api': 0.0, 'funding_rate': 0.0, 'oi_change_24h': 0.0,
            'pct_7d': 0.0, 'vol_7d': 0.0, 'ema20_gap': 0.0, 'ema50_gap': 0.0,
            'macd_hist': 0.0, 'dist_top20d': 0.0, 'dist_bottom20d': 0.0,
            'volume_to_mcap': 0.0
        }
    
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
            score = max(-1, min(1, score))  # Clip between -1 and 1
            
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
            
            # Get market data - try real data first, fallback to mock
            market_data = None
            if self.market_fetcher:
                try:
                    self.log(f"Fetching real-time market data for {symbol}...")
                    market_data = self.market_fetcher.get_12h_ohlcv_data(f"{symbol}USDT")
                except Exception as e:
                    self.log(f"MarketDataFetcher failed: {e}, using simple fetcher")
            
            if not market_data:
                self.log(f"Using simple price fetcher for {symbol}...")
                market_data = self._fetch_real_price_simple(symbol)
            
            if not market_data:
                raise ValueError(f"Failed to fetch market data for {symbol}")
            
            # Log data source
            current_price = market_data.get('current_price', 0)
            self.log(f"Current price for {symbol}: ${current_price:,.2f}")
            
            # Calculate features
            if self.market_fetcher:
                features = self.market_fetcher.calculate_features(market_data)
            else:
                features = self._calculate_features_simple(market_data)
            
            # Fetch sentiment analysis if texts provided
            sentiment_features = {"sentiment_score_api": 0.0, "sentiment_confidence": 0.0}
            if sentiment_texts:
                try:
                    sentiment_features = self.fetch_sentiment_analysis(sentiment_texts)
                except Exception as e:
                    self.log(f"Sentiment API failed: {e}, using mock sentiment")
                    sentiment_features = self._mock_sentiment_analysis(sentiment_texts)
                features.update(sentiment_features)
            else:
                # Use mock sentiment if no texts provided
                sentiment_features = self._mock_sentiment_analysis(["Market analysis"])
                features.update(sentiment_features)
            
            # Mock ML inference (in production, this would call the Netlify function)
            ml_result = self._mock_ml_inference(features)
            
            # Calculate absolute price changes (no percentage symbols)
            current_price = market_data['current_price']
            price_change_1h = current_price * features.get('pct_1h', 0)
            price_change_24h = current_price * features.get('pct_24h', 0)
            
            # Combine all data
            analysis_result = {
                "asset": symbol,
                "timestamp": datetime.now().isoformat(),
                "current_price": current_price,
                "price_data_last_24h": {
                    "open": market_data['open'][0] if market_data['open'] else 0,
                    "high": max(market_data['high']) if market_data['high'] else 0,
                    "low": min(market_data['low']) if market_data['low'] else 0,
                    "close": market_data['close'][-1] if market_data['close'] else 0
                },
                "price_change_absolute": {
                    "1h": round(price_change_1h, 2),
                    "24h": round(price_change_24h, 2)
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
        
        # Add some randomness (without numpy)
        import random
        long_score += random.uniform(-0.05, 0.05)
        short_score += random.uniform(-0.05, 0.05)
        
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
    print("CryptoRocket Integrated Analysis System")
    print("=" * 50)
    
    # Initialize analyzer
    analyzer = CryptoAnalyzer(verbose=True)
    
    # Analyze top cryptocurrencies
    print("\nAnalyzing top cryptocurrencies...")
    results = analyzer.get_top_cryptocurrencies(limit=5)
    
    # Display results
    print("\nAnalysis Results:")
    print("-" * 80)
    
    for result in results:
        if "error" in result:
            print(f"ERROR {result['asset']}: {result['error']}")
            continue
            
        asset = result['asset']
        price = result['current_price']
        signal = result['ml_prediction']['signal']
        confidence = result['ml_prediction']['confidence']
        sentiment = result['ai_sentiment']['label']
        
        print(f"\n{asset}")
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
    
    print("\nAnalysis completed!")
    
    # Save results to file
    output_file = f"crypto_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"Results saved to: {output_file}")

if __name__ == "__main__":
    main()
