## Guia de Treinamento (LR v1)

1. Dados e janelas

- Coleta: preços OHLCV minuto/hora, volumes, market cap, derivativos (funding, OI), textos (notícias/social).
- Janelas: treino 180d, validação 30d em walk‑forward; blackout 1h após t para rótulo 24h.

2. Features

- Construir conforme `docs/FEATURES_SPEC.md` até t (sem look‑ahead).
- Winsorize p1–p99 (fit no treino), imputação (mediana/constante), z‑score (fit no treino).

3. Rótulos

- LONG=1 se ret(t→t+24h)>+1%; SHORT=1 se ret<-1%; NEUTRAL=0 caso contrário.
- Criar vetores y_long e y_short (one-vs-rest).

4. Modelo

- Regressão Logística (L2). Grid C: [1e-3, 3e-3, 1e-2, 3e-2, 1e-1, 3e-1, 1, 3, 10].
- Balanceamento: `class_weight='balanced'`.

5. Calibração

- Out-of-fold por janela (k=5) → Platt ou Isotonic (preferir Isotonic se >5k amostras/dobra).
- Salvar parâmetros/step-function no artefato.

6. Seleção de limiares

- Otimizar θ_long, θ_short maximizando Sharpe no backtest de validação (com custos/slippage).
- Métricas secundárias: AUC (ovr), F1 por classe, MCC, Brier.

7. Export de artefatos

- `artifacts/model_artifacts.json`: `feature_order`, `winsor_limits`, `imputer_values`, `scaler_mean/std`, `lr_*` (coef/intercept/calibration), `thresholds`, `vol_model`, `kappa`, `version`, `seed`, `metrics`.

8. Execução (scaffold)

```bash
python ml/train.py --out artifacts/model_artifacts.json --samples 5000 --seed 20251010
```

- Substituir gerador sintético por dados reais na função `build_features_placeholder` e rótulos em `make_labels_placeholder`.

9. Observabilidade

- Logar versão de dados, hparams, seed, score da validação por janela; salvar relatório em `docs/BACKTEST.md`.
