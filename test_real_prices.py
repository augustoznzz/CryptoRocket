#!/usr/bin/env python3
"""
Teste simples para demonstrar o sistema com preços reais
Usa apenas bibliotecas padrão do Python
"""

import json
import time
import random
from datetime import datetime

def fetch_real_price_simple(symbol):
    """Fetch real price using simple HTTP request"""
    try:
        import urllib.request
        import urllib.parse
        
        # Use CoinGecko API (simpler, no API key needed)
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={symbol.lower()}&vs_currencies=usd&include_24hr_change=true"
        
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode())
            
        if symbol.lower() in data:
            coin_data = data[symbol.lower()]
            current_price = coin_data.get('usd', 0)
            change_24h = coin_data.get('usd_24h_change', 0)
            return {
                'current_price': current_price,
                'change_24h_pct': change_24h,
                'change_24h_abs': current_price * (change_24h / 100),
                'source': 'CoinGecko API'
            }
    except Exception as e:
        print(f"Erro ao buscar preço real para {symbol}: {e}")
        return None

def generate_realistic_features(price_data):
    """Generate realistic features based on real price data"""
    if not price_data:
        return {}
    
    current_price = price_data['current_price']
    change_24h_pct = price_data['change_24h_pct']
    
    # Calculate realistic features based on real data
    return {
        'pct_1h': random.uniform(-0.02, 0.02),  # 1h change
        'pct_24h': change_24h_pct / 100,  # Real 24h change
        'ret_log_24h': (change_24h_pct / 100) * 0.8,  # Log return approximation
        'vol_24h': abs(change_24h_pct / 100) * 2,  # Volatility based on 24h change
        'rsi_14': 50 + (change_24h_pct / 2),  # RSI based on momentum
        'volume_ratio_7d': random.uniform(0.8, 1.2),
        'log_mcap': 20 + random.uniform(-2, 2),
        'sentiment_score_api': change_24h_pct / 100 * 0.5,  # Sentiment based on price change
        'funding_rate': random.uniform(-0.002, 0.002),
        'oi_change_24h': random.uniform(-0.1, 0.1),
        'pct_7d': change_24h_pct / 100 * 2,  # 7d change approximation
        'vol_7d': abs(change_24h_pct / 100) * 1.5,
        'ema20_gap': change_24h_pct / 100 * 0.3,
        'ema50_gap': change_24h_pct / 100 * 0.2,
        'macd_hist': change_24h_pct / 100 * 0.1,
        'dist_top20d': random.uniform(-0.1, 0.1),
        'dist_bottom20d': random.uniform(-0.1, 0.1),
        'volume_to_mcap': random.uniform(1e-8, 1e-6)
    }

def mock_ml_inference_real(features):
    """Mock ML inference using real features"""
    pct_24h = features.get('pct_24h', 0)
    rsi = features.get('rsi_14', 50)
    sentiment = features.get('sentiment_score_api', 0)
    vol = features.get('vol_24h', 0)
    
    # More realistic prediction based on actual market conditions
    long_score = 0.0
    short_score = 0.0
    
    # LONG factors based on real data
    if pct_24h > 0.02: long_score += 0.4  # Strong positive momentum
    elif pct_24h > 0.005: long_score += 0.2  # Moderate positive
    
    if rsi < 70: long_score += 0.1  # Not overbought
    if sentiment > 0.1: long_score += 0.3  # Positive sentiment
    elif sentiment > 0: long_score += 0.1
    
    if vol > 0.03: long_score += 0.1  # Good volatility for momentum
    
    # SHORT factors based on real data
    if pct_24h < -0.02: short_score += 0.4  # Strong negative momentum
    elif pct_24h < -0.005: short_score += 0.2  # Moderate negative
    
    if rsi > 30: short_score += 0.1  # Not oversold
    if sentiment < -0.1: short_score += 0.3  # Negative sentiment
    elif sentiment < 0: short_score += 0.1
    
    if vol > 0.03: short_score += 0.1  # High volatility
    
    # Add some market noise
    long_score += random.uniform(-0.05, 0.05)
    short_score += random.uniform(-0.05, 0.05)
    
    # Normalize probabilities
    total_score = long_score + short_score + 0.3  # Base neutral
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
    
    return {
        "probabilities": {
            "long": round(prob_long, 3),
            "short": round(prob_short, 3),
            "neutral": round(prob_neutral, 3)
        },
        "signal": signal,
        "confidence": round(max(prob_long, prob_short), 3)
    }

def analyze_crypto_real(symbol):
    """Analyze cryptocurrency with real price data"""
    print(f"\n=== Analisando {symbol} com dados REAIS ===")
    
    # Fetch real price data
    price_data = fetch_real_price_simple(symbol)
    
    if not price_data:
        print(f"Falha ao obter dados reais para {symbol}")
        return None
    
    current_price = price_data['current_price']
    change_24h_abs = price_data['change_24h_abs']
    change_24h_pct = price_data['change_24h_pct']
    
    print(f"Preco atual: ${current_price:,.2f}")
    print(f"Mudanca 24h: ${change_24h_abs:+,.2f} ({change_24h_pct:+.2f}%)")
    print(f"Fonte: {price_data['source']}")
    
    # Generate features based on real data
    features = generate_realistic_features(price_data)
    
    # Run ML inference
    ml_result = mock_ml_inference_real(features)
    
    # Display results
    print(f"Sinal ML: {ml_result['signal']}")
    print(f"Confianca: {ml_result['confidence']:.1%}")
    print(f"Probabilidades:")
    print(f"   LONG: {ml_result['probabilities']['long']:.1%}")
    print(f"   SHORT: {ml_result['probabilities']['short']:.1%}")
    print(f"   NEUTRAL: {ml_result['probabilities']['neutral']:.1%}")
    
    # Technical indicators
    print(f"Indicadores Tecnicos:")
    print(f"   RSI: {features['rsi_14']:.1f}")
    print(f"   Volatilidade 24h: {features['vol_24h']:.3f}")
    print(f"   Sentimento: {features['sentiment_score_api']:.3f}")
    
    return {
        'symbol': symbol,
        'current_price': current_price,
        'change_24h_abs': change_24h_abs,
        'change_24h_pct': change_24h_pct,
        'signal': ml_result['signal'],
        'confidence': ml_result['confidence'],
        'probabilities': ml_result['probabilities'],
        'features': features
    }

def main():
    """Main function"""
    print("CryptoRocket - Analise com Precos REAIS")
    print("=" * 50)
    print("Demonstrando o sistema com dados reais das últimas 24 horas")
    print("Fonte: CoinGecko API (dados em tempo real)")
    print()
    
    # Cryptocurrencies to analyze
    symbols = ['bitcoin', 'ethereum', 'solana', 'cardano', 'dogecoin']
    
    results = []
    
    for symbol in symbols:
        try:
            result = analyze_crypto_real(symbol)
            if result:
                results.append(result)
            time.sleep(1)  # Rate limiting
        except Exception as e:
            print(f"Erro ao analisar {symbol}: {e}")
    
    # Summary
    print("\n" + "=" * 50)
    print("RESUMO DA ANALISE")
    print("=" * 50)
    
    if results:
        total_long = sum(1 for r in results if r['signal'] == 'LONG')
        total_short = sum(1 for r in results if r['signal'] == 'SHORT')
        total_neutral = sum(1 for r in results if r['signal'] == 'NEUTRAL')
        
        avg_confidence = sum(r['confidence'] for r in results) / len(results)
        total_change_24h = sum(r['change_24h_abs'] for r in results)
        
        print(f"Sinais gerados: {len(results)}")
        print(f"   LONG: {total_long}")
        print(f"   SHORT: {total_short}")
        print(f"   NEUTRAL: {total_neutral}")
        print(f"Confianca media: {avg_confidence:.1%}")
        print(f"Mudanca total 24h: ${total_change_24h:+,.2f}")
        
        print(f"\nPrecos atuais:")
        for result in results:
            print(f"   {result['symbol'].upper()}: ${result['current_price']:,.2f} ({result['change_24h_pct']:+.2f}%)")
        
        # Save results
        output_file = f"real_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\nResultados salvos em: {output_file}")
    
    print("\nAnalise concluida com dados REAIS das ultimas 24 horas!")

if __name__ == "__main__":
    main()
