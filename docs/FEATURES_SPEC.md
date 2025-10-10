## Especificação de Features (v1)

Legenda: aplicar nesta ordem → Clip/Winsorize → Imputação (mediana ou valor) → Z-score.

| nome                | descrição               | origem/fórmula                        | transformação                     |
| ------------------- | ----------------------- | ------------------------------------- | --------------------------------- |
| pct_1h              | variação percentual 1h  | (price_t / price_t-1h − 1)            | clip p1–p99; imput=0; z-score     |
| pct_24h             | variação percentual 24h | (price_t / price_t-24h − 1)           | clip p1–p99; imput=0; z-score     |
| ret_log_24h         | retorno log 24h         | ln(price_t) − ln(price_t−24h)         | clip p1–p99; imput=0; z-score     |
| vol_24h             | vol realizada 24h       | sqrt(∑ r_i^2 intradiário)             | clip p1–p99; imput=0; z-score     |
| rsi_14              | RSI 14 períodos         | cálculo clássico RSI                  | clip [0,100]→z; imput=50; z-score |
| volume_ratio_7d     | vol_24h / média_vol_7d  | volume_24h / mean(volume_1d,7d)       | clip p1–p99; imput=1; z-score     |
| log_mcap            | log market cap          | ln(market_cap_usd)                    | clip p1–p99; imput=0; z-score     |
| sentiment_score_api | sentimento IA [-1,1]    | média ponderada por confiança (6–24h) | clip [-1,1]; imput=0; z-score     |
| funding_rate        | taxa de funding         | derivativos (se disp.)                | clip p1–p99; imput=0; z-score     |
| oi_change_24h       | variação OI 24h         | (OI_t / OI_t−24h − 1)                 | clip p1–p99; imput=0; z-score     |
| pct_7d              | variação 7d             | (price_t / price_t−7d − 1)            | clip p1–p99; imput=0; z-score     |
| vol_7d              | vol realizada 7d        | sqrt(∑ r_d^2 diário, 7d)              | clip p1–p99; imput=0; z-score     |
| ema20_gap           | % acima/abaixo EMA20    | (price / EMA20 − 1)                   | clip p1–p99; imput=0; z-score     |
| ema50_gap           | % acima/abaixo EMA50    | (price / EMA50 − 1)                   | clip p1–p99; imput=0; z-score     |
| macd_hist           | MACD histograma         | (EMA12−EMA26)−EMA9                    | clip p1–p99; imput=0; z-score     |
| dist_top20d         | distância do topo 20d   | (price / max20d − 1)                  | clip p1–p99; imput=0; z-score     |
| dist_bottom20d      | distância do fundo 20d  | (price / min20d − 1)                  | clip p1–p99; imput=0; z-score     |
| volume_to_mcap      | liquidez relativa       | volume_24h / market_cap               | clip p1–p99; imput=0; z-score     |

- Flags binárias: `is_missing_*` para cada feature com imputação; mantidas fora de `feature_order` por ora (não usadas na LR v1).
- Outliers: winsorização p1–p99 por feature com base em treino; limites salvos em `winsor_limits`.
- Normalização: `scaler_mean`, `scaler_std` do treino (não recalcular em produção).

Rótulos (lookahead 24h):

- LONG=1 se retorno_future_24h > +1.0% ; SHORT=1 se retorno_future_24h < −1.0%; NEUTRAL=0 caso contrário.

Observações:

- Dados faltantes em derivativos/livro/IA são comuns → imput=0 e flag.
- `vol_24h_expected` usada para potencial vem de um modelo simples de vol realizada rolling (artefatos `vol_model`).
