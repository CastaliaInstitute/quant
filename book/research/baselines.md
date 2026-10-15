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

These additional probability baselines are only meaningful when the corresponding point-in-time fields have coverage. When a fold lacks volatility variation or archived phase values, its conditional forecast falls back to the fold base rate. The evaluator records fold-level and pooled Brier/log-loss results for all baselines, plus paired issuer × calendar-quarter pigeonhole bootstrap intervals for baseline-minus-logit score improvements; positive differences favor the logistic model because lower Brier/log loss is better. It withholds intervals unless there are at least ten issuer clusters and ten calendar-quarter clusters, and reports when sparse issuer-quarter crossings prevent enough valid draws. The intervals are descriptive and conditional on fixed out-of-sample predictions; this resampling does not model serial dependence across quarters. The eighteen-disclosure seed cohort still fails the minimum event gate and produces no fitted result. The crossed resampling design follows the pigeonhole bootstrap literature; it is distinct from multiway cluster-robust standard errors ([Owen, 2007](https://doi.org/10.1214/07-AOAS122); [Cameron, Gelbach & Miller, 2011](https://doi.org/10.1198/jbes.2010.07136)).

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

## Turn issuer risk estimates into inspectable weights

Before a learned policy allocates across companies, compare simple portfolios under the same universe and constraints. Equal weight is a transparent reference; inverse-volatility weights reduce the allocation to higher-volatility issuers. A per-issuer cap can leave part of the portfolio in cash. This tiny example uses invented volatility estimates and labels only the resulting weights; it does not calculate or imply portfolio returns.

```{code-cell} ipython3
issuer_names = ["Issuer A", "Issuer B", "Issuer C", "Issuer D"]
estimated_annual_volatility = [0.60, 0.45, 0.30, 0.20]
inverse_volatility = [
    1 / estimated_annual_volatility[0],
    1 / estimated_annual_volatility[1],
    1 / estimated_annual_volatility[2],
    1 / estimated_annual_volatility[3],
]
inverse_volatility_total = sum(inverse_volatility)
inverse_volatility_weights = [
    inverse_volatility[0] / inverse_volatility_total,
    inverse_volatility[1] / inverse_volatility_total,
    inverse_volatility[2] / inverse_volatility_total,
    inverse_volatility[3] / inverse_volatility_total,
]
issuer_weight_cap = 0.40
capped_weights = [min(weight, issuer_weight_cap) for weight in inverse_volatility_weights]
cash_weight = 1.0 - sum(capped_weights)

for issuer, equal_weight, raw_weight, capped_weight in zip(
    issuer_names, [0.25, 0.25, 0.25, 0.25], inverse_volatility_weights, capped_weights
):
    print(issuer, "equal-weight:", round(equal_weight, 3), "inverse-vol:", round(raw_weight, 3), "capped:", round(capped_weight, 3))
print("Residual cash after issuer caps:", round(cash_weight, 3))
```

The cap is applied without reallocating excess to the other names, so the remainder stays in cash. The reusable Python baseline in [`quantlab.portfolio.allocate_portfolio`](https://github.com/CastaliaInstitute/quant/blob/main/src/quantlab/portfolio.py) implements equal-weight and inverse-volatility weights with issuer and optional sector caps, and reports excluded assets and residual cash. It does not estimate volatility, covariance, or returns. An empirical application must estimate risk from training-window returns only, define how missing and newly listed issuers enter, add total-risk limits, and charge for turnover and execution. Compare every rule using the same time-aligned net returns and XBI/SPY benchmarks; a plausible weight vector is not evidence of a profitable portfolio.

## Apply close-time targets on the next return period

The portfolio backtest uses one-row-lagged target weights. This short synthetic example makes the timing, idle cash, traded notional, and net returns visible. The first period stays in cash because the first target is only observed at that period's close.

```{code-cell} ipython3
synthetic_asset_returns = [[0.01, 0.02], [-0.03, 0.01], [0.05, -0.01]]
close_time_targets = [[0.50, 0.50], [0.20, 0.40], [0.50, 0.20]]
portfolio_net_returns = [0.0, 0.0, 0.0]
previous_weight_0 = 0.0
previous_weight_1 = 0.0
cost_bps = 10.0

for day in range(3):
    if day == 0:
        weight_0 = 0.0
        weight_1 = 0.0
    else:
        weight_0 = close_time_targets[day - 1][0]
        weight_1 = close_time_targets[day - 1][1]
    cash_weight = 1.0 - weight_0 - weight_1
    turnover = abs(weight_0 - previous_weight_0) + abs(weight_1 - previous_weight_1)
    gross_return = weight_0 * synthetic_asset_returns[day][0] + weight_1 * synthetic_asset_returns[day][1]
    transaction_cost = turnover * cost_bps / 10000.0
    net_return = gross_return - transaction_cost
    portfolio_net_returns[day] = net_return
    print("period", day + 1, "cash:", round(cash_weight, 2), "turnover:", round(turnover, 2), "cost:", round(transaction_cost, 5), "net return:", round(net_return, 5))
    previous_weight_0 = weight_0
    previous_weight_1 = weight_1
```

This is an accounting illustration over three invented periods, not an annualized performance estimate. The Python [`portfolio_backtest`](https://github.com/CastaliaInstitute/quant/blob/main/src/quantlab/portfolio.py) applies the same lag to a date-indexed return panel, checks weight and missing-return constraints, and returns equity, turnover, costs, and net returns for the selected scorecard.

## Sensitivity is part of the result

For event-risk forecasting, report calibration, Brier score or log loss for declared event-loss classes, discrimination with confidence intervals, tail-event precision/recall, and performance by phase, indication, issuer, and period. Compare against the historical training-fold base rate. For any trading rule, vary costs, execution lag, event timestamp convention, and feature windows. Show the full range; a single favorable setting is evidence of fragility, not a reason to hide alternatives.
