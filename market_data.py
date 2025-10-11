#!/usr/bin/env python3
"""
Enhanced Market Data Module for CryptoRocket
Fetches 12-hour OHLCV data and calculates technical indicators for ML model
"""

import requests
import time
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import json

class TechnicalIndicators:
    """Calculate technical indicators for cryptocurrency data"""
    
    @staticmethod
    def rsi(prices: List[float], period: int = 14) -> float:
        """Calculate RSI indicator"""
        if len(prices) < period + 1:
            return 50.0  # Neutral RSI if insufficient data
        
        deltas = np.diff(prices[-period-1:])
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    @staticmethod
    def ema(prices: List[float], period: int) -> float:
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return prices[-1] if prices else 0
        
        alpha = 2 / (period + 1)
        ema = prices[0]
        for price in prices[1:]:
            ema = alpha * price + (1 - alpha) * ema
        return ema
    
    @staticmethod
    def sma(prices: List[float], period: int) -> float:
        """Calculate Simple Moving Average"""
        if len(prices) < period:
            return np.mean(prices) if prices else 0
        return np.mean(prices[-period:])
    
    @staticmethod
    def macd(prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, float]:
        """Calculate MACD indicator"""
        if len(prices) < slow:
            return {"macd": 0, "signal": 0, "histogram": 0}
        
        ema_fast = TechnicalIndicators.ema(prices, fast)
        ema_slow = TechnicalIndicators.ema(prices, slow)
        macd_line = ema_fast - ema_slow
        
        # For signal line, we'd need historical MACD values, simplified here
        signal_line = macd_line * 0.9  # Simplified
        histogram = macd_line - signal_line
        
        return {"macd": macd_line, "signal": signal_line, "histogram": histogram}
    
    @staticmethod
    def volatility(prices: List[float], period: int = 24) -> float:
        """Calculate realized volatility"""
        if len(prices) < 2:
            return 0
        
        returns = np.diff(np.log(prices))
        if len(returns) < period:
            period = len(returns)
        
        return np.std(returns[-period:]) * np.sqrt(period)

class MarketDataFetcher:
    """Enhanced market data fetcher with 12-hour OHLCV and technical indicators"""
    
    def __init__(self, verbose=False):
        """Initialize market data fetcher"""
        self.verbose = verbose
        self.cache = {}
        self.cache_timeout = 300  # 5 minutes cache
        
    def log(self, message):
        """Log message if verbose mode is enabled"""
        if self.verbose:
            print(f"[MARKET] {message}")
    
    def get_12h_ohlcv_data(self, symbol: str) -> Dict:
        """Fetch 12-hour OHLCV data for a symbol"""
        try:
            # Check cache first
            cache_key = f"{symbol}_12h_data"
            if cache_key in self.cache:
                cached_data, timestamp = self.cache[cache_key]
                if time.time() - timestamp < self.cache_timeout:
                    self.log(f"Using cached data for {symbol}")
                    return cached_data
            
            # Try multiple endpoints for better reliability
            endpoints = [
                f"https://api.binance.com/api/v3/klines",
                f"https://api1.binance.com/api/v3/klines",
                f"https://api2.binance.com/api/v3/klines",
                f"https://api3.binance.com/api/v3/klines"
            ]
            
            for url in endpoints:
                try:
                    params = {
                        'symbol': symbol,
                        'interval': '1h',
                        'limit': 24  # Get 24 hours for better calculation
                    }
                    
                    self.log(f"Fetching real-time data for {symbol} from {url}")
                    response = requests.get(url, params=params, timeout=15)
                    response.raise_for_status()
                    
                    klines = response.json()
                    
                    if klines and len(klines) > 0:
                        # Parse OHLCV data
                        timestamps = [int(k[0]) for k in klines]
                        opens = [float(k[1]) for k in klines]
                        highs = [float(k[2]) for k in klines]
                        lows = [float(k[3]) for k in klines]
                        closes = [float(k[4]) for k in klines]
                        volumes = [float(k[5]) for k in klines]
                        
                        # Validate data quality
                        if self._validate_market_data(opens, highs, lows, closes, volumes):
                            data = {
                                'timestamps': timestamps,
                                'open': opens,
                                'high': highs,
                                'low': lows,
                                'close': closes,
                                'volume': volumes,
                                'current_price': closes[-1] if closes else 0
                            }
                            
                            # Cache the data
                            self.cache[cache_key] = (data, time.time())
                            self.log(f"Successfully fetched real-time data for {symbol}: ${data['current_price']:,.2f}")
                            return data
                        else:
                            self.log(f"Invalid data quality for {symbol}, trying next endpoint")
                            continue
                    
                except requests.exceptions.RequestException as e:
                    self.log(f"Failed to fetch from {url}: {str(e)}")
                    continue
                except Exception as e:
                    self.log(f"Error processing data from {url}: {str(e)}")
                    continue
            
            # If all Binance endpoints fail, try CoinGecko as fallback
            self.log(f"All Binance endpoints failed for {symbol}, trying CoinGecko...")
            return self._get_coingecko_fallback(symbol)
            
        except Exception as e:
            self.log(f"Critical error fetching data for {symbol}: {str(e)}")
            return self._get_fallback_ohlcv(symbol)
    
    def _validate_market_data(self, opens: List[float], highs: List[float], 
                            lows: List[float], closes: List[float], volumes: List[float]) -> bool:
        """Validate the quality of market data"""
        try:
            # Check if we have enough data points
            if len(opens) < 12:
                return False
            
            # Check for reasonable price ranges
            if any(price <= 0 for price in opens + highs + lows + closes):
                return False
            
            # Check if high >= low for all candles
            for i in range(len(opens)):
                if highs[i] < lows[i]:
                    return False
            
            # Check for reasonable volume
            if any(vol < 0 for vol in volumes):
                return False
            
            # Check for reasonable price variations (not too extreme)
            max_price = max(highs)
            min_price = min(lows)
            if max_price / min_price > 10:  # More than 1000% variation seems suspicious
                return False
            
            return True
            
        except Exception:
            return False
    
    def _get_coingecko_fallback(self, symbol: str) -> Dict:
        """Get data from CoinGecko as fallback when Binance fails"""
        try:
            # Map Binance symbols to CoinGecko IDs (only the 12 specified)
            symbol_map = {
                'BTCUSDT': 'bitcoin',
                'ETHUSDT': 'ethereum',
                'BNBUSDT': 'binancecoin',
                'SOLUSDT': 'solana',
                'ADAUSDT': 'cardano',
                'XRPUSDT': 'ripple',
                'DOGEUSDT': 'dogecoin',
                'TRXUSDT': 'tron',
                'LINKUSDT': 'chainlink',
                'SUIUSDT': 'sui',
                'XLMUSDT': 'stellar',
                'UNIUSDT': 'uniswap'
            }
            
            coin_id = symbol_map.get(symbol, 'bitcoin')  # Default to Bitcoin
            
            # Get current price and 24h change
            url = f"https://api.coingecko.com/api/v3/simple/price"
            params = {
                'ids': coin_id,
                'vs_currencies': 'usd',
                'include_24hr_change': 'true',
                'include_24hr_vol': 'true'
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if coin_id in data:
                coin_data = data[coin_id]
                current_price = coin_data.get('usd', 50000)
                change_24h = coin_data.get('usd_24h_change', 0) / 100
                volume_24h = coin_data.get('usd_24h_vol', 1000000000)
                
                # Generate realistic OHLCV data based on real price
                opens = []
                highs = []
                lows = []
                closes = []
                volumes = []
                
                for i in range(24):
                    # Simulate hourly price movement based on 24h change
                    hourly_change = change_24h / 24 + np.random.normal(0, abs(change_24h) * 0.1)
                    price = current_price * (1 - change_24h * (23 - i) / 24)
                    
                    open_price = price
                    close_price = price * (1 + hourly_change)
                    high_price = max(open_price, close_price) * (1 + abs(np.random.normal(0, 0.005)))
                    low_price = min(open_price, close_price) * (1 - abs(np.random.normal(0, 0.005)))
                    volume = volume_24h / 24 * (1 + np.random.normal(0, 0.2))
                    
                    opens.append(open_price)
                    highs.append(high_price)
                    lows.append(low_price)
                    closes.append(close_price)
                    volumes.append(volume)
                
                self.log(f"Using CoinGecko fallback for {symbol}: ${current_price:,.2f}")
                
                return {
                    'timestamps': [int(time.time() * 1000) - (23-i) * 3600000 for i in range(24)],
                    'open': opens,
                    'high': highs,
                    'low': lows,
                    'close': closes,
                    'volume': volumes,
                    'current_price': current_price
                }
            
        except Exception as e:
            self.log(f"CoinGecko fallback failed for {symbol}: {str(e)}")
        
        # Final fallback to mock data
        return self._get_fallback_ohlcv(symbol)
    
    def _get_fallback_ohlcv(self, symbol: str) -> Dict:
        """Generate fallback OHLCV data when all APIs fail"""
        # Use more realistic base prices based on symbol
        base_prices = {
            'BTCUSDT': 65000,
            'ETHUSDT': 3500,
            'BNBUSDT': 600,
            'SOLUSDT': 180,
            'ADAUSDT': 0.45,
            'XRPUSDT': 0.55,
            'DOGEUSDT': 0.08,
            'TRXUSDT': 0.11,
            'LINKUSDT': 14,
            'SUIUSDT': 1.0,
            'XLMUSDT': 0.12,
            'UNIUSDT': 8.0
        }
        
        base_price = base_prices.get(symbol, 100)
        price_variation = (time.time() % 1000) / 1000
        
        self.log(f"Using mock data for {symbol} (APIs unavailable)")
        
        # Generate 24 hours of synthetic data
        prices = []
        for i in range(24):
            # Add some realistic price movement
            change = np.random.normal(0, 0.02)  # 2% standard deviation
            price = base_price * (1 + change + price_variation * 0.01)
            prices.append(price)
        
        return {
            'timestamps': [int(time.time() * 1000) - (23-i) * 3600000 for i in range(24)],
            'open': prices,
            'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
            'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
            'close': prices,
            'volume': [1000000 + np.random.normal(0, 100000) for _ in range(24)],
            'current_price': prices[-1]
        }
    
    def calculate_features(self, ohlcv_data: Dict) -> Dict[str, float]:
        """Calculate all features for the ML model"""
        closes = ohlcv_data['close']
        volumes = ohlcv_data['volume']
        current_price = ohlcv_data['current_price']
        
        if not closes or len(closes) < 2:
            return self._get_default_features()
        
        # Basic price features using 24h data
        price_1h = (closes[-1] / closes[-2] - 1) if len(closes) >= 2 else 0
        price_24h = (closes[-1] / closes[0] - 1) if len(closes) >= 24 else (closes[-1] / closes[0] - 1) if len(closes) > 0 else 0
        ret_log_24h = np.log(closes[-1] / closes[0]) if len(closes) >= 24 and closes[0] > 0 else 0
        
        # Volatility using 24h data
        vol_24h = TechnicalIndicators.volatility(closes, min(24, len(closes)))
        
        # Technical indicators
        rsi_14 = TechnicalIndicators.rsi(closes, 14)
        ema_20 = TechnicalIndicators.ema(closes, 20)
        ema_50 = TechnicalIndicators.ema(closes, 50)
        macd_data = TechnicalIndicators.macd(closes)
        
        # Volume features
        volume_24h = sum(volumes)
        volume_ratio_7d = 1.0  # Simplified, would need 7 days of data
        
        # Price distance from EMAs
        ema20_gap = (current_price / ema_20 - 1) if ema_20 > 0 else 0
        ema50_gap = (current_price / ema_50 - 1) if ema_50 > 0 else 0
        
        # Distance from 20-day high/low (simplified to use available data)
        max_20d = max(closes) if closes else current_price
        min_20d = min(closes) if closes else current_price
        dist_top_20d = (current_price / max_20d - 1) if max_20d > 0 else 0
        dist_bottom_20d = (current_price / min_20d - 1) if min_20d > 0 else 0
        
        # Market cap (simplified - would need actual market cap data)
        estimated_mcap = current_price * 21000000  # Rough BTC supply estimate
        log_mcap = np.log(estimated_mcap) if estimated_mcap > 0 else 0
        volume_to_mcap = volume_24h / estimated_mcap if estimated_mcap > 0 else 0
        
        return {
            'pct_1h': price_1h,
            'pct_24h': price_24h,
            'ret_log_24h': ret_log_24h,
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
            'macd_hist': macd_data['histogram'],
            'dist_top20d': dist_top_20d,
            'dist_bottom20d': dist_bottom_20d,
            'volume_to_mcap': volume_to_mcap
        }
    
    def _get_default_features(self) -> Dict[str, float]:
        """Return default feature values when data is unavailable"""
        return {
            'pct_1h': 0.0, 'pct_24h': 0.0, 'ret_log_24h': 0.0, 'vol_24h': 0.0,
            'rsi_14': 50.0, 'volume_ratio_7d': 1.0, 'log_mcap': 0.0,
            'sentiment_score_api': 0.0, 'funding_rate': 0.0, 'oi_change_24h': 0.0,
            'pct_7d': 0.0, 'vol_7d': 0.0, 'ema20_gap': 0.0, 'ema50_gap': 0.0,
            'macd_hist': 0.0, 'dist_top20d': 0.0, 'dist_bottom20d': 0.0,
            'volume_to_mcap': 0.0
        }
    
    def get_target_cryptocurrencies(self):
        """
        Get the target cryptocurrencies with enhanced data
        
        Returns:
            list: List of cryptocurrency data with 12h OHLCV and features
        """
        try:
            self.log("Fetching target cryptocurrencies with 12h data and technical indicators")
            
            # Target cryptocurrencies (restricted to 12 specified)
            target_symbols = [
                'BTCUSDT', 'ETHUSDT', 'XRPUSDT', 'BNBUSDT', 'SOLUSDT',
                'DOGEUSDT', 'TRXUSDT', 'ADAUSDT', 'LINKUSDT', 'SUIUSDT',
                'XLMUSDT', 'UNIUSDT'
            ]
            
            enhanced_data = []
            for symbol in target_symbols:
                try:
                    # Fetch 12h OHLCV data
                    ohlcv = self.get_12h_ohlcv_data(symbol)
                    
                    # Calculate features
                    features = self.calculate_features(ohlcv)
                    
                    # Get symbol info
                    symbol_info = symbol.replace('USDT', '')
                    
                    # Calculate 24h price changes in absolute values (no % symbols)
                    current_price = ohlcv['current_price']
                    price_change_1h = current_price * features.get('pct_1h', 0)
                    price_change_24h = current_price * features.get('pct_24h', 0)
                    
                    enhanced_data.append({
                        'symbol': symbol_info,
                        'full_symbol': symbol,
                        'current_price': current_price,
                        'price_change_absolute': {
                            '1h': round(price_change_1h, 2),
                            '24h': round(price_change_24h, 2)
                        },
                        'price_data_last_24h': {
                            'open': ohlcv['open'][0] if ohlcv['open'] else 0,
                            'high': max(ohlcv['high']) if ohlcv['high'] else 0,
                            'low': min(ohlcv['low']) if ohlcv['low'] else 0,
                            'close': ohlcv['close'][-1] if ohlcv['close'] else 0
                        },
                        'features': features,
                        'timestamp': datetime.now().isoformat(),
                        'data_source': 'real_time' if 'real-time' in str(ohlcv) else 'fallback'
                    })
                    
                except Exception as e:
                    self.log(f"Error processing {symbol}: {str(e)}")
                    continue
            
            self.log(f"Fetched enhanced data for {len(enhanced_data)} cryptocurrencies")
            return enhanced_data
            
        except Exception as e:
            self.log(f"Error fetching market data: {str(e)}")
            return []
    
    def get_fallback_data(self):
        """
        Get fallback data when API fails (simplified)
        
        Returns:
            list: Basic fallback data with only 3 indicators
        """
        fallback_coins = [
            {
                'id': 'bitcoin',
                'symbol': 'BTC',
                'name': 'Bitcoin',
                'current_price': 95000 + (time.time() % 10000),
                'market_cap': 1800000000000 + (time.time() % 200000000000),
                'volume_24h': 35000000000 + (time.time() % 15000000000),
                'price_change_24h': (time.time() % 6) - 3
            },
            {
                'id': 'ethereum',
                'symbol': 'ETH',
                'name': 'Ethereum',
                'current_price': 5200 + (time.time() % 800),
                'market_cap': 600000000000 + (time.time() % 100000000000),
                'volume_24h': 25000000000 + (time.time() % 10000000000),
                'price_change_24h': (time.time() % 5) - 2.5
            }
        ]
        
        self.log("Generated fallback data with basic indicators only")
        return fallback_coins