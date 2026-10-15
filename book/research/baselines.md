---
jupytext:
  text_representation:
    extension: .md
    format_name: myst
    format_version: '0.13'
kernelspec:
  name: python3
  display_name: Python 3
  language: python
---

# Baselines: Give the Hypothesis a Fair Contest

```{raw} html
<p class="castalia-kicker">INQUIRY 001 · COMPARISON BEFORE CLAIM</p>
```

A catalyst-risk model must add value over simple reference forecasts. The gated evaluator now compares the training-fold downside base rate, a volatility-tertile historical rate, a phase-conditioned historical rate, and a regularized logistic model. The volatility and phase rates use training-fold rows only and are shrunk toward that fold's base rate with prior strength 5, so tiny groups do not produce an all-or-nothing probability. SPY/XBI context is included among candidate logistic features. If evaluating tradable policies later, also include cash, buy-and-hold, and a transparent pre-event exit rule. Keep the same events, timestamps, market data, and costs across comparisons.

These additional probability baselines are only meaningful when the corresponding point-in-time fields have coverage. When a fold lacks volatility variation or archived phase values, its conditional forecast falls back to the fold base rate. The evaluator records fold-level and pooled Brier/log-loss results for all baselines, plus paired issuer-cluster bootstrap intervals for baseline-minus-logit score improvements; positive differences favor the logistic model because lower Brier/log loss is better. It withholds those intervals below five issuer clusters; issuer clustering also does not remove shared market-date dependence. The nine-disclosure seed cohort still fails the minimum event gate and produces no fitted result.

## Calculate a small set of interpretable quantities

The following synthetic returns demonstrate how a researcher can inspect cumulative growth, annualized volatility, Sharpe ratio, and drawdown. The annualization factor is an assumption, not a property of the sample.

```{code-cell} ipython3
net_returns = [0.002, -0.003, 0.004, 0.001, -0.002, 0.003, -0.001, 0.002]
periods_per_year = 252

equity = 1.0
peak = 1.0
max_drawdown = 0.0
for value in net_returns:
    equity = equity * (1.0 + value)
    peak = max(peak, equity)
    drawdown = equity / peak - 1.0
    max_drawdown = min(max_drawdown, drawdown)

mean_return = sum(net_returns) / len(net_returns)
variance = sum((value - mean_return) ** 2 for value in net_returns) / (len(net_returns) - 1)
annualized_volatility = variance ** 0.5 * periods_per_year ** 0.5
sharpe = mean_return * periods_per_year ** 0.5 / (variance ** 0.5) if variance > 0 else 0

print("Synthetic cumulative growth:", round(equity - 1.0, 4))
print("Illustrative annualized volatility:", round(annualized_volatility, 4))
print("Illustrative Sharpe ratio:", round(sharpe, 3))
print("Maximum drawdown:", round(max_drawdown, 4))
```

## Sensitivity is part of the result

For event-risk forecasting, report calibration, Brier score or log loss for declared event-loss classes, discrimination with confidence intervals, tail-event precision/recall, and performance by phase, indication, issuer, and period. Compare against the historical training-fold base rate. For any trading rule, vary costs, execution lag, event timestamp convention, and feature windows. Show the full range; a single favorable setting is evidence of fragility, not a reason to hide alternatives.
