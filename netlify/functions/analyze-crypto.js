const https = require('https');

// Sistema de rate limiting baseado em IP
const rateLimitStore = new Map(); // IP -> { lastRequest: timestamp, count: number }

// Lista específica de criptomoedas para análise (12 solicitadas)
const TARGET_CRYPTOCURRENCIES = [
  'bitcoin', 'ethereum', 'ripple', 'binancecoin', 'solana',
  'dogecoin', 'tron', 'cardano', 'chainlink', 'sui', 'stellar', 'uniswap'
];

// Função para obter IP real do usuário
function getClientIP(event) {
  // Netlify Functions pode ter diferentes headers para IP
  const headers = event.headers || {};
  
  // Tentar diferentes headers de IP
  const ip = headers['x-forwarded-for'] || 
             headers['x-real-ip'] || 
             headers['cf-connecting-ip'] || 
             headers['x-client-ip'] ||
             'unknown';
  
  // Se x-forwarded-for contém múltiplos IPs, pegar o primeiro
  return ip.split(',')[0].trim();
}

// Função para verificar rate limit
function checkRateLimit(ip) {
  const now = Date.now(); // Usar timestamp do servidor, não do cliente
  const oneHour = 60 * 60 * 1000; // 1 hora em milissegundos
  
  if (!rateLimitStore.has(ip)) {
    // Primeira solicitação deste IP
    rateLimitStore.set(ip, {
      lastRequest: now,
      count: 1
    });
    return { allowed: true, remainingTime: 0 };
  }
  
  const record = rateLimitStore.get(ip);
  const timeSinceLastRequest = now - record.lastRequest;
  
  if (timeSinceLastRequest < oneHour) {
    // Ainda dentro do período de 1 hora
    const remainingTime = Math.ceil((oneHour - timeSinceLastRequest) / 1000 / 60); // em minutos
    return { 
      allowed: false, 
      remainingTime,
      message: `Rate limit exceeded. Try again in ${remainingTime} minutes.`
    };
  } else {
    // Passou 1 hora, resetar contador
    rateLimitStore.set(ip, {
      lastRequest: now,
      count: 1
    });
    return { allowed: true, remainingTime: 0 };
  }
}

// Função para limpar IPs antigos (manutenção)
function cleanupOldIPs() {
  const now = Date.now();
  const oneDay = 24 * 60 * 60 * 1000; // 1 dia
  
  for (const [ip, record] of rateLimitStore.entries()) {
    if (now - record.lastRequest > oneDay) {
      rateLimitStore.delete(ip);
    }
  }
}

// Limpar IPs antigos a cada 100 solicitações
let requestCount = 0;

// Função principal da Netlify Function
exports.handler = async (event, context) => {
  // Habilitar CORS
  const headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS'
  };

  // Responder a requisições OPTIONS (preflight)
  if (event.httpMethod === 'OPTIONS') {
    return {
      statusCode: 200,
      headers,
      body: ''
    };
  }

  try {
    // Obter IP do cliente
    const clientIP = getClientIP(event);
    console.log(`🔍 Request from IP: ${clientIP}`);
    
    // Verificar rate limit
    const rateLimitCheck = checkRateLimit(clientIP);
    
    if (!rateLimitCheck.allowed) {
      console.log(`🚫 Rate limit exceeded for IP ${clientIP}: ${rateLimitCheck.message}`);
      return {
        statusCode: 429, // Too Many Requests
        headers,
        body: JSON.stringify({
          success: false,
          error: 'Rate limit exceeded',
          message: rateLimitCheck.message,
          remainingTime: rateLimitCheck.remainingTime,
          timestamp: new Date().toISOString()
        })
      };
    }
    
    // Incrementar contador de solicitações para limpeza
    requestCount++;
    if (requestCount % 100 === 0) {
      cleanupOldIPs();
      console.log(`🧹 Cleaned up old IPs. Current store size: ${rateLimitStore.size}`);
    }
    
    console.log('✅ Rate limit check passed, starting cryptocurrency analysis...');
    
    let targetCoins;
    let source = 'API';
    let retryCount = 0;
    const maxRetries = 3;
    
    // Tentar obter dados da API com retry logic
    while (retryCount < maxRetries) {
      try {
        console.log(`Attempt ${retryCount + 1} to fetch data from CoinGecko API...`);
        targetCoins = await getTargetCryptocurrencies();
        
        if (targetCoins && targetCoins.length > 0) {
          console.log(`✅ Success! Cryptocurrencies obtained from API: ${targetCoins.length}`);
          console.log(`Sample real data - BTC price: $${targetCoins.find(c => c.symbol === 'BTC')?.current_price}`);
          source = 'Real-Time API';
          break; // Sucesso, sair do loop
        } else {
          throw new Error('API returned empty data');
        }
      } catch (apiError) {
        retryCount++;
        console.log(`❌ API attempt ${retryCount} failed:`, apiError.message);
        
        if (retryCount >= maxRetries) {
          console.log('🚨 All API attempts failed, using fallback data');
          targetCoins = getFallbackData();
          source = 'Fallback (API failed)';
        } else {
          console.log(`⏳ Waiting 2 seconds before retry ${retryCount + 1}...`);
          await new Promise(resolve => setTimeout(resolve, 2000)); // Esperar 2 segundos
        }
      }
    }
    
    if (targetCoins.length === 0) {
      throw new Error('No cryptocurrencies available for analysis');
    }
    
    // Generate simple and fast analysis (based on available data)
    const analysisResults = generateSimpleAnalysis(targetCoins);
    
    // Enrich top results with historical data snapshot (3 months ago) and 6-month mini-series (T-8..T-3)
    const enriched = await enrichWithHistorical(analysisResults);
    console.log(`Analyses generated: ${analysisResults.length}`);
    
    return {
      statusCode: 200,
      headers,
      body: JSON.stringify({
        success: true,
        results: enriched,
        total_analyzed: targetCoins.length,
        timestamp: new Date().toISOString().split('T')[0],
        message: `Technical analysis completed - Top 5 best opportunities selected (${source})`,
        data_source: source,
        api_attempts: retryCount,
        rate_limit_info: {
          ip: clientIP,
          next_request_allowed: new Date(Date.now() + 60 * 60 * 1000).toISOString()
        }
      })
    };
  } catch (error) {
    console.error('Analysis error:', error.message);
    
    return {
      statusCode: 500,
      headers,
      body: JSON.stringify({
        success: false,
        error: 'Technical analysis error: ' + error.message,
        timestamp: new Date().toISOString()
      })
    };
  }
};

// Validar que o preço atual está dentro da faixa de 24h
function validatePriceInRange(coin) {
  if (!coin.high_24h || !coin.low_24h) {
    // Se não tiver high/low, calcular baseado no current_price e variação percentual
    const variation = Math.abs(coin.price_change_percentage_24h || 2) / 100;
    coin.high_24h = coin.current_price * (1 + variation);
    coin.low_24h = coin.current_price * (1 - variation);
    console.log(`📊 ${coin.symbol}: Calculando faixa 24h baseada na variação (${coin.price_change_percentage_24h?.toFixed(2)}%)`);
  }
  
  // Log da faixa atual
  console.log(`📈 ${coin.symbol}: Preço $${coin.current_price?.toFixed(2)} | Faixa: $${coin.low_24h?.toFixed(2)} - $${coin.high_24h?.toFixed(2)}`);
  
  // Garantir que current_price esteja dentro da faixa [low_24h, high_24h]
  if (coin.current_price > coin.high_24h) {
    const oldPrice = coin.current_price;
    coin.current_price = coin.high_24h * 0.98; // 98% do high
    console.log(`⚠️  ${coin.symbol}: Preço ajustado de $${oldPrice?.toFixed(2)} para $${coin.current_price?.toFixed(2)} (98% do high_24h)`);
  }
  if (coin.current_price < coin.low_24h) {
    const oldPrice = coin.current_price;
    coin.current_price = coin.low_24h * 1.02; // 102% do low
    console.log(`⚠️  ${coin.symbol}: Preço ajustado de $${oldPrice?.toFixed(2)} para $${coin.current_price?.toFixed(2)} (102% do low_24h)`);
  }
  
  // Validação final
  if (coin.current_price >= coin.low_24h && coin.current_price <= coin.high_24h) {
    console.log(`✅ ${coin.symbol}: Preço validado dentro da faixa 24h`);
  }
  
  return coin;
}

// Dados de fallback para quando a API falhar
function getFallbackData() {
  const fallbackCoins = [
    (() => {
      const current_price = 95000 + Math.random() * 5000; // $95k - $100k (mais realista)
      const price_change_percentage_24h = (Math.random() - 0.5) * 4; // ±2%
      const variation = Math.abs(price_change_percentage_24h) / 100;
      return {
        id: 'bitcoin',
        symbol: 'BTC',
        name: 'Bitcoin',
        current_price: current_price,
        market_cap: 1800000000000 + Math.random() * 200000000000, // $1.8T - $2.0T
        price_change_24h: current_price * price_change_percentage_24h / 100,
        price_change_percentage_24h: price_change_percentage_24h,
        volume_24h: 35000000000 + Math.random() * 15000000000, // $35B - $50B
        high_24h: current_price * (1 + variation * 1.2),
        low_24h: current_price * (1 - variation * 1.2)
      };
    })(),
    (() => {
      const current_price = 3500 + Math.random() * 300; // $3.5k - $3.8k (mais realista)
      const price_change_percentage_24h = (Math.random() - 0.5) * 4; // ±2%
      const variation = Math.abs(price_change_percentage_24h) / 100;
      return {
        id: 'ethereum',
        symbol: 'ETH',
        name: 'Ethereum',
        current_price: current_price,
        market_cap: 400000000000 + Math.random() * 50000000000, // $400B - $450B
        price_change_24h: current_price * price_change_percentage_24h / 100,
        price_change_percentage_24h: price_change_percentage_24h,
        volume_24h: 15000000000 + Math.random() * 5000000000, // $15B - $20B
        high_24h: current_price * (1 + variation * 1.2),
        low_24h: current_price * (1 - variation * 1.2)
      };
    })(),
    (() => {
      const current_price = 0.55 + Math.random() * 0.1; // $0.55 - $0.65 (mais realista)
      const price_change_percentage_24h = (Math.random() - 0.5) * 4; // ±2%
      const variation = Math.abs(price_change_percentage_24h) / 100;
      return {
        id: 'ripple',
        symbol: 'XRP',
        name: 'XRP',
        current_price: current_price,
        market_cap: 30000000000 + Math.random() * 10000000000, // $30B - $40B
        price_change_24h: current_price * price_change_percentage_24h / 100,
        price_change_percentage_24h: price_change_percentage_24h,
        volume_24h: 2000000000 + Math.random() * 1000000000, // $2B - $3B
        high_24h: current_price * (1 + variation * 1.2),
        low_24h: current_price * (1 - variation * 1.2)
      };
    })(),
    (() => {
      const current_price = 580 + Math.random() * 40; // $580 - $620 (preço realista do BNB)
      const price_change_percentage_24h = (Math.random() - 0.5) * 4; // ±2%
      const variation = Math.abs(price_change_percentage_24h) / 100;
      return {
        id: 'binancecoin',
        symbol: 'BNB',
        name: 'BNB',
        current_price: current_price,
        market_cap: 85000000000 + Math.random() * 10000000000, // $85B - $95B
        price_change_24h: current_price * price_change_percentage_24h / 100,
        price_change_percentage_24h: price_change_percentage_24h,
        volume_24h: 2000000000 + Math.random() * 1000000000, // $2B - $3B
        high_24h: current_price * (1 + variation * 1.2),
        low_24h: current_price * (1 - variation * 1.2)
      };
    })(),
    (() => {
      const current_price = 180 + Math.random() * 20; // $180 - $200 (mais realista)
      const price_change_percentage_24h = (Math.random() - 0.5) * 6; // ±3%
      const variation = Math.abs(price_change_percentage_24h) / 100;
      return {
        id: 'solana',
        symbol: 'SOL',
        name: 'Solana',
        current_price: current_price,
        market_cap: 80000000000 + Math.random() * 20000000000, // $80B - $100B
        price_change_24h: current_price * price_change_percentage_24h / 100,
        price_change_percentage_24h: price_change_percentage_24h,
        volume_24h: 3000000000 + Math.random() * 1000000000, // $3B - $4B
        high_24h: current_price * (1 + variation * 1.2),
        low_24h: current_price * (1 - variation * 1.2)
      };
    })(),
    (() => {
      const current_price = 0.45 + Math.random() * 0.1; // $0.45 - $0.55 (mais realista)
      const price_change_percentage_24h = (Math.random() - 0.5) * 5; // ±2.5%
      const variation = Math.abs(price_change_percentage_24h) / 100;
      return {
        id: 'cardano',
        symbol: 'ADA',
        name: 'Cardano',
        current_price: current_price,
        market_cap: 15000000000 + Math.random() * 5000000000, // $15B - $20B
        price_change_24h: current_price * price_change_percentage_24h / 100,
        price_change_percentage_24h: price_change_percentage_24h,
        volume_24h: 500000000 + Math.random() * 300000000, // $500M - $800M
        high_24h: current_price * (1 + variation * 1.2),
        low_24h: current_price * (1 - variation * 1.2)
      };
    })(),
    (() => {
      const current_price = 12 + Math.random() * 2; // $12 - $14 (mais realista)
      const price_change_percentage_24h = (Math.random() - 0.5) * 5; // ±2.5%
      const variation = Math.abs(price_change_percentage_24h) / 100;
      return {
        id: 'chainlink',
        symbol: 'LINK',
        name: 'Chainlink',
        current_price: current_price,
        market_cap: 7000000000 + Math.random() * 2000000000, // $7B - $9B
        price_change_24h: current_price * price_change_percentage_24h / 100,
        price_change_percentage_24h: price_change_percentage_24h,
        volume_24h: 400000000 + Math.random() * 200000000, // $400M - $600M
        high_24h: current_price * (1 + variation * 1.2),
        low_24h: current_price * (1 - variation * 1.2)
      };
    })()
  ];
  
  // Apply validation to all fallback coins
  const validatedCoins = fallbackCoins.map(coin => validatePriceInRange(coin));
  
  console.log(`🔄 Fallback data generated: ${validatedCoins.length} cryptocurrencies`);
  console.log(`⚠️  Note: These are simulated values. Real-time data is preferred.`);
  return validatedCoins;
}

// Obter dados das criptomoedas específicas
function getTargetCryptocurrencies() {
  return new Promise((resolve, reject) => {
    // Primeiro tentar Binance, depois CoinGecko, depois CoinCap
    tryBinance()
      .then(resolve)
      .catch(() => {
        console.log('🔄 Binance failed, trying CoinGecko API...');
        return tryCoinGecko();
      })
      .then(resolve)
      .catch(() => {
        console.log('🔄 CoinGecko failed, trying CoinCap API...');
        return tryCoinCap();
      })
      .then(resolve)
      .catch(reject);
  });
}

// Tentar API Binance (mais confiável para preços reais)
function tryBinance() {
  return new Promise((resolve, reject) => {
    // Mapear símbolos para os usados pela Binance
    const binanceSymbols = {
      'bitcoin': 'BTCUSDT',
      'ethereum': 'ETHUSDT', 
      'ripple': 'XRPUSDT',
      'binancecoin': 'BNBUSDT',
      'solana': 'SOLUSDT',
      'dogecoin': 'DOGEUSDT',
      'tron': 'TRXUSDT',
      'cardano': 'ADAUSDT',
      'chainlink': 'LINKUSDT',
      'sui': 'SUIUSDT',
      'stellar': 'XLMUSDT',
      'uniswap': 'UNIUSDT'
    };
    
    const symbols = Object.values(binanceSymbols).join(',');
    const url = `https://api.binance.com/api/v3/ticker/24hr?symbols=[${symbols.split(',').map(s => `"${s}"`).join(',')}]`;
    
    console.log('🔍 Trying Binance API...');
    
    const req = https.get(url, (res) => {
      let data = '';
      
      res.on('data', (chunk) => {
        data += chunk;
      });
      
      res.on('end', () => {
        try {
          if (res.statusCode !== 200) {
            reject(new Error(`Binance HTTP ${res.statusCode}`));
            return;
          }
          
          const jsonData = JSON.parse(data);
          if (!Array.isArray(jsonData) || jsonData.length === 0) {
            reject(new Error('Binance returned empty data'));
            return;
          }

          const result = jsonData.map(coin => {
            // Mapear de volta para os IDs originais
            const symbolMap = Object.entries(binanceSymbols).find(([_, symbol]) => symbol === coin.symbol);
            const originalId = symbolMap ? symbolMap[0] : coin.symbol.toLowerCase();
            
            return validatePriceInRange({
              id: originalId,
              symbol: coin.symbol.replace('USDT', ''),
              name: coin.symbol.replace('USDT', ''),
              current_price: parseFloat(coin.lastPrice),
              market_cap: 0, // Binance não fornece market cap diretamente
              price_change_percentage_24h: parseFloat(coin.priceChangePercent),
              volume_24h: parseFloat(coin.volume),
              high_24h: parseFloat(coin.highPrice),
              low_24h: parseFloat(coin.lowPrice)
            });
          });
          
          console.log(`✅ Binance success: ${result.length} cryptocurrencies`);
          console.log(`Sample real data - BTC price: $${result.find(c => c.symbol === 'BTC')?.current_price}`);
          resolve(result);
        } catch (parseError) {
          reject(new Error('Binance parse error'));
        }
      });
    });
    
    req.on('error', () => reject(new Error('Binance connection error')));
    req.setTimeout(8000, () => {
      req.destroy();
      reject(new Error('Binance timeout'));
    });
  });
}

// Tentar API CoinGecko
function tryCoinGecko() {
  return new Promise((resolve, reject) => {
    const coinIds = TARGET_CRYPTOCURRENCIES.join(',');
    const url = `https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids=${coinIds}&order=market_cap_desc&sparkline=false&price_change_percentage=24h`;
    
    console.log('🔍 Trying CoinGecko API...');
    
    const req = https.get(url, (res) => {
      let data = '';
      
      res.on('data', (chunk) => {
        data += chunk;
      });
      
      res.on('end', () => {
        try {
          if (res.statusCode !== 200) {
            reject(new Error(`CoinGecko HTTP ${res.statusCode}`));
            return;
          }
          
          const jsonData = JSON.parse(data);
          if (jsonData.length === 0) {
            reject(new Error('CoinGecko returned empty data'));
            return;
          }

          const result = jsonData.map(coin => validatePriceInRange({
            id: coin.id,
            symbol: coin.symbol.toUpperCase(),
            name: coin.name,
            current_price: coin.current_price,
            market_cap: coin.market_cap,
            // Do not return 24h percentage change to frontend
            price_change_percentage_24h: coin.price_change_percentage_24h,
            volume_24h: coin.total_volume,
            high_24h: coin.high_24h,
            low_24h: coin.low_24h
          }));
          
          console.log(`✅ CoinGecko success: ${result.length} cryptocurrencies`);
          resolve(result);
        } catch (parseError) {
          reject(new Error('CoinGecko parse error'));
        }
      });
    });
    
    req.on('error', () => reject(new Error('CoinGecko connection error')));
    req.setTimeout(8000, () => {
      req.destroy();
      reject(new Error('CoinGecko timeout'));
    });
  });
}

// Tentar API CoinCap (alternativa)
function tryCoinCap() {
  return new Promise((resolve, reject) => {
    // CoinCap usa IDs diferentes, mapear para os símbolos
    const symbols = ['bitcoin', 'ethereum', 'ripple', 'binance-coin', 'solana', 'cardano', 'chainlink', 'dogecoin', 'tron', 'stellar', 'uniswap', 'sui'];
    const url = `https://api.coincap.io/v2/assets?ids=${symbols.join(',')}`;
    
    console.log('🔍 Trying CoinCap API...');
    
    const req = https.get(url, (res) => {
      let data = '';
      
      res.on('data', (chunk) => {
        data += chunk;
      });
      
      res.on('end', () => {
        try {
          if (res.statusCode !== 200) {
            reject(new Error(`CoinCap HTTP ${res.statusCode}`));
            return;
          }
          
          const jsonData = JSON.parse(data);
          if (!jsonData.data || jsonData.data.length === 0) {
            reject(new Error('CoinCap returned empty data'));
            return;
          }

          const result = jsonData.data.map(coin => validatePriceInRange({
            id: coin.id,
            symbol: coin.symbol.toUpperCase(),
            name: coin.name,
            current_price: parseFloat(coin.priceUsd),
            market_cap: parseFloat(coin.marketCapUsd),
            // Do not return 24h percentage change to frontend
            price_change_percentage_24h: parseFloat(coin.changePercent24Hr),
            volume_24h: parseFloat(coin.volumeUsd24Hr),
            high_24h: coin.high24Hr ? parseFloat(coin.high24Hr) : parseFloat(coin.priceUsd) * 1.05,
            low_24h: coin.low24Hr ? parseFloat(coin.low24Hr) : parseFloat(coin.priceUsd) * 0.95
          }));
          
          console.log(`✅ CoinCap success: ${result.length} cryptocurrencies`);
          resolve(result);
        } catch (parseError) {
          reject(new Error('CoinCap parse error'));
        }
      });
    });
    
    req.on('error', () => reject(new Error('CoinCap connection error')));
    req.setTimeout(8000, () => {
      req.destroy();
      reject(new Error('CoinCap timeout'));
    });
  });
}

// Gerar análise simples e rápida
function generateSimpleAnalysis(coins) {
  const results = [];
  
  for (const coin of coins) {
    try {
      // Basic analysis based on available data
      const analysis = analyzeCoin(coin);
      
      if (analysis.score > 0.2) { // Low score to include more results
        results.push({
          symbol: coin.symbol,
          name: coin.name,
          current_price: coin.current_price,
          // Do NOT return any 24h percentage change to the frontend
          type: analysis.type,
          potential_gain: analysis.potentialGain,
          signal: analysis.description,
          score: analysis.score,
          volume_24h: coin.volume_24h
        });
      }
          } catch (error) {
        console.error(`Error analyzing ${coin.symbol}:`, error.message);
        continue;
      }
  }
  
      // Sort by score and return top 5
  return results
    .sort((a, b) => b.score - a.score)
    .slice(0, 5);
}

// Helper: add months to a Date safely (UTC)
function addMonthsUTC(date, months) {
  const d = new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate()));
  const year = d.getUTCFullYear();
  const month = d.getUTCMonth();
  const day = d.getUTCDate();
  const targetMonthIndex = month + months;
  const targetYear = year + Math.floor(targetMonthIndex / 12);
  const targetMonth = ((targetMonthIndex % 12) + 12) % 12;
  // Clamp day to end of month
  const lastDay = new Date(Date.UTC(targetYear, targetMonth + 1, 0)).getUTCDate();
  const targetDay = Math.min(day, lastDay);
  return new Date(Date.UTC(targetYear, targetMonth, targetDay));
}

// Fetch historical daily prices for a coin (up to 365 days) and compute monthly closes for specific months
async function fetchMonthlySeriesForCoinGecko(coinId) {
  return new Promise((resolve, reject) => {
    const url = `https://api.coingecko.com/api/v3/coins/${coinId}/market_chart?vs_currency=usd&days=365&interval=daily`;
    const req = https.get(url, (res) => {
      let data = '';
      res.on('data', (chunk) => { data += chunk; });
      res.on('end', () => {
        try {
          if (res.statusCode !== 200) return reject(new Error(`CoinGecko market_chart HTTP ${res.statusCode}`));
          const json = JSON.parse(data);
          if (!json.prices || !Array.isArray(json.prices)) return reject(new Error('market_chart malformed'));
          resolve(json.prices); // [ [tsMs, price], ... ]
        } catch (e) {
          reject(new Error('market_chart parse error'));
        }
      });
    });
    req.on('error', () => reject(new Error('market_chart connection error')));
    req.setTimeout(8000, () => { req.destroy(); reject(new Error('market_chart timeout')); });
  });
}

// Compute SMA(N) on a numeric array; returns array with same length with nulls for not-enough prefix
function computeSMA(values, period) {
  const out = new Array(values.length).fill(null);
  let sum = 0;
  for (let i = 0; i < values.length; i++) {
    sum += values[i];
    if (i >= period) sum -= values[i - period];
    if (i >= period - 1) out[i] = sum / period;
  }
  return out;
}

// Compute RSI on closes using period N (Wilder's smoothing simplified for small N)
function computeRSI(closes, period) {
  const rsi = new Array(closes.length).fill(null);
  for (let i = period; i < closes.length; i++) {
    let gains = 0, losses = 0;
    for (let j = i - period + 1; j <= i; j++) {
      const change = closes[j] - closes[j - 1];
      if (change >= 0) gains += change; else losses -= change;
    }
    const avgGain = gains / period;
    const avgLoss = losses / period;
    if (avgLoss === 0) {
      rsi[i] = 100;
    } else {
      const rs = avgGain / avgLoss;
      rsi[i] = 100 - (100 / (1 + rs));
    }
  }
  return rsi;
}

// Enrich top results with historical snapshot and 6-month mini-series
async function enrichWithHistorical(results) {
  // Work on a copy
  const top = results.slice(0, 5);
  const now = new Date();
  const asOf = addMonthsUTC(now, -3); // 3 months ago
  
  // target months indices: T-8..T-3 inclusive (6 months)
  const months = [];
  for (let m = -8; m <= -3; m++) {
    const d = addMonthsUTC(now, m);
    months.push({ year: d.getUTCFullYear(), month: d.getUTCMonth() });
  }

  // Map symbol->id guess: we need coin.id; results come from tryCoinGecko or tryCoinCap mapping earlier
  // We can't guarantee id on results, so try to infer from name/symbol by searching original TARGET_CRYPTOCURRENCIES match; fall back to lowercase name
  // To minimize additional API calls, assume CoinGecko ids are lowercased names without spaces, except common ones already covered.

  async function enrichOne(r) {
    // Attempt to guess CoinGecko id
    let idGuess = (r.name || r.symbol || '').toLowerCase();
    // Common fixes
    const map = {
      'btc': 'bitcoin', 'bitcoin': 'bitcoin',
      'eth': 'ethereum', 'ethereum': 'ethereum',
      'xrp': 'ripple', 'ripple': 'ripple',
      'bnb': 'binancecoin', 'binance coin': 'binancecoin', 'binancecoin': 'binancecoin',
      'sol': 'solana', 'solana': 'solana',
      'ada': 'cardano', 'cardano': 'cardano',
      'dot': 'polkadot', 'polkadot': 'polkadot',
      'link': 'chainlink', 'chainlink': 'chainlink',
      'usdt': 'tether', 'tether': 'tether',
      'usdc': 'usd-coin', 'usd-coin': 'usd-coin',
      'doge': 'dogecoin', 'dogecoin': 'dogecoin',
      'trx': 'tron', 'tron': 'tron',
      'xlm': 'stellar', 'stellar': 'stellar',
      'uni': 'uniswap', 'uniswap': 'uniswap',
      'sui': 'sui',
      'dai': 'dai'
    };
    const id = map[idGuess] || map[(r.symbol || '').toLowerCase()] || map[(r.name || '').toLowerCase()] || idGuess.replace(/\s+/g, '-');

    try {
      const daily = await fetchMonthlySeriesForCoinGecko(id);
      // Build month->last price map
      const monthKey = (d) => `${d.getUTCFullYear()}-${d.getUTCMonth()}`;
      const monthClose = new Map();
      for (const [ts, price] of daily) {
        const d = new Date(ts);
        const key = `${d.getUTCFullYear()}-${d.getUTCMonth()}`;
        // Keep last one seen in month (since data is chronological)
        monthClose.set(key, price);
      }

      const series = months.map(({ year, month }) => {
        const key = `${year}-${month}`;
        const d = new Date(Date.UTC(year, month, 1));
        const price = monthClose.has(key) ? monthClose.get(key) : null;
        return { dateISO: d.toISOString().split('T')[0], label: `${year}-${String(month + 1).padStart(2,'0')}`, price };
      });

      // Compute SMA(3) and RSI(3) over available prices
      const closes = series.map(p => p.price ?? 0);
      const sma3 = computeSMA(closes, 3);
      const rsi3 = computeRSI(closes, 3);
      for (let i = 0; i < series.length; i++) {
        series[i].sma = sma3[i] !== null ? Number(sma3[i]) : null;
        series[i].rsi = rsi3[i] !== null ? Number(rsi3[i]) : null;
      }

      // As-of price = last available in as-of month (T-3)
      const asOfKey = `${asOf.getUTCFullYear()}-${asOf.getUTCMonth()}`;
      const asOfPrice = monthClose.has(asOfKey) ? monthClose.get(asOfKey) : null;

      // Approx 24h change at end of as-of month: take last two entries in that month
      let asOfChangePct = 0;
      try {
        const inMonth = daily.filter(([ts]) => {
          const d = new Date(ts);
          return d.getUTCFullYear() === asOf.getUTCFullYear() && d.getUTCMonth() === asOf.getUTCMonth();
        });
        if (inMonth.length >= 2) {
          const pPrev = inMonth[inMonth.length - 2][1];
          const pLast = inMonth[inMonth.length - 1][1];
          asOfChangePct = ((pLast - pPrev) / pPrev) * 100;
        }
      } catch (_) {}

      return {
        ...r,
        as_of_date: asOf.toISOString().split('T')[0],
        as_of_price: asOfPrice != null ? Number(asOfPrice) : r.current_price,
        // Do NOT return 24h change percentage
        historical: { months: series }
      };
    } catch (e) {
      // On failure, return original result without historical
      return {
        ...r,
        as_of_date: asOf.toISOString().split('T')[0],
        as_of_price: r.current_price,
        historical: null,
        historical_error: e.message
      };
    }
  }

  const out = [];
  for (const r of top) {
    // Sequential to be gentle with rate limits
    // eslint-disable-next-line no-await-in-loop
    const enhanced = await enrichOne(r);
    out.push(enhanced);
  }
  return out;
}

// Analisar uma criptomoeda individual
function analyzeCoin(coin) {
  // Momentum and turnover proxies (per-coin)
  const pct = Number(coin.price_change_percentage_24h || 0);
  const momentumAbs = Math.min(Math.abs(pct) / 12, 1); // ~0..1 for |12%|
  const turnoverRaw = (coin.volume_24h || 0) / Math.max(coin.market_cap || 1, 1);
  const turnover = Math.min(Math.max(turnoverRaw, 0), 1); // clamp 0..1

  // Market cap factor: smaller caps → higher potential (more volatility)
  const capLog = Math.log10((coin.market_cap || 1));
  const capNorm = Math.max(0, Math.min(1, (12 - capLog) / 4)); // 0 (mega caps) .. 1 (small caps)

  // Score primarily for ranking (0..1)
  let score = 0.35
    + 0.40 * momentumAbs
    + 0.15 * Math.min(turnover * 4, 1)
    + 0.10 * capNorm;
  score = Math.max(0, Math.min(1, score));

  // Adaptive potential (conservative range ~3–20% based on volatility/turnover/cap)
  const volExp = Math.min(1, momentumAbs * 0.7 + Math.min(turnover * 3, 1) * 0.3);
  const potentialGain = Math.round((3 + 17 * (0.55 * volExp + 0.45 * capNorm)) * 10) / 10;

  // Direction/type using sign and confidence
  let type = 'NEUTRAL';
  if (pct >= 1 || (pct > 0 && score >= 0.6)) type = 'LONG';
  if (pct <= -1 || (pct < 0 && score >= 0.6)) type = 'SHORT';
  if (score < 0.4) type = 'SHORT';

  const description = generateDescription(coin, type, potentialGain, score);

  return { type, score, potentialGain, description };
}

// Generate analysis description
function generateDescription(coin, type, potentialGain, score) {
  let description = `Technical Analysis ${coin.symbol}:\n`;
  
  // Trend based on 24h change (without showing numerical percentage)
  description += `• Trend: ${coin.price_change_percentage_24h > 0 ? 'Bullish' : coin.price_change_percentage_24h < 0 ? 'Bearish' : 'Neutral'} (24h)\n`;
  
  // Current price - rounded with thousand separators
  const formattedPrice = Math.round(coin.current_price).toLocaleString('en-US');
  description += `• Current Price: $${formattedPrice}\n`;
  
  // Volume - with appropriate units
  if (coin.volume_24h > 1000000000) {
    const volumeB = (coin.volume_24h / 1000000000).toFixed(1);
    description += `• Volume: Very High ($${volumeB}B)\n`;
  } else if (coin.volume_24h > 100000000) {
    const volumeM = (coin.volume_24h / 1000000).toFixed(1);
    description += `• Volume: High ($${volumeM}M)\n`;
  } else {
    const volumeM = (coin.volume_24h / 1000000).toFixed(1);
    description += `• Volume: Medium ($${volumeM}M)\n`;
  }
  
  // Market cap - with appropriate units
  if (coin.market_cap > 1000000000000) {
    const marketCapT = (coin.market_cap / 1000000000000).toFixed(1);
    description += `• Market Cap: Very High ($${marketCapT}T)\n`;
  } else if (coin.market_cap > 10000000000) {
    const marketCapB = (coin.market_cap / 1000000000).toFixed(1);
    description += `• Market Cap: High ($${marketCapB}B)\n`;
  } else {
    const marketCapB = (coin.market_cap / 1000000000).toFixed(1);
    description += `• Market Cap: Medium ($${marketCapB}B)\n`;
  }
  
  const action = type === 'LONG' ? 'Buy' : (type === 'SHORT' ? 'Sell/Short' : 'Hold/Neutral');
  description += `\nStrategy: ${action} with target +${potentialGain}%`;
  description += `\nConfidence: ${Math.round(score * 100)}%`;
  
  return description;
}
