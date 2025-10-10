## Backtest 24h (Walk-Forward)

Estratégia: entrar no fechamento t quando sinal ≠ NEUTRAL; sair em t+24h. Custos: 10 bps por lado; slippage: 5 bps.

Métricas:

- Sharpe, retorno anualizado, max drawdown, turnover, hit rate.
- AUC (LONG/SHORT), F1 por classe, MCC, Brier, calibração (reliability curves).

Comparativos:

- Baseline heurístico antigo (apenas para relatório, fora de produção).
- LR v1 (calibrado) com e sem sentimento IA.

Checklist de sanity/leak:

- Features só até t; blackout 1h; sem médias que incluam t+.
- Hiperparâmetros e normalização fitados apenas no treino.

Resultados (placeholder):

- Sharpe baseline: 0.45 | Sharpe LR v1: 1.10
- AUC LONG: 0.72 | AUC SHORT: 0.74
- Impacto sentimento IA: +0.06 Sharpe em ativos com alto noticiário.

Limitações e próximos passos:

- Cobertura derivativos incompleta em alts; melhorar imput/flags.
- Vol previsto simples; testar GARCH/EGARCH ou HAR-RV.
- Afinar θ por ativo/classe de liquidez.
