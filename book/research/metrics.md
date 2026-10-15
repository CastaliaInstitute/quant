# Return Metrics: The Portfolio Scorecard

```{raw} html
<p class="castalia-kicker">NET OF COSTS · OUT OF SAMPLE · BESIDE A BENCHMARK</p>
```

Quant. uses a compact scorecard rather than a single leaderboard number. For biotech/pharma catalyst work, lead with **net CAGR, annualized volatility, Sharpe ratio, maximum drawdown, turnover, cost sensitivity, and event-window downside**. Pair strategy results with a biotech-sector benchmark and broad-market context on the same dates. Report the full return path, sample length, and inference unit beside every summary. A long daily panel can still represent only a few independent catalyst events.

## Decision hierarchy

The primary metric depends on the research claim; do not collapse model skill and portfolio return into one score.

| Claim being evaluated | Primary evidence | Secondary diagnostics |
| --- | --- | --- |
| Catalyst-downside probability model | Out-of-sample Brier score and log loss versus a training-fold base-rate forecast | Calibration by probability bin, event rate, ROC AUC when defined, issuer/phase/regime slices |
| Historical catalyst event study | Market-model cumulative abnormal return over declared event windows, with issuer, event, and calendar coverage | Raw return, SPY/XBI controls, pre-event estimation count, window sensitivity, and event-time precision |
| Downside-risk target sensitivity | Compare the raw issuer −10% event-window label with the −10% market-model CAR label using identical chronological folds | Label prevalence, missing factor-model coverage, calibration, event/issuer counts, and fold-by-fold scores |
| Event-risk model skill | Paired OOS Brier/log-loss improvement over training-only baselines | Issuer × calendar-quarter pigeonhole bootstrap intervals, withheld when either dimension has fewer than ten clusters |
| Investable strategy or RL policy | Net compounded return and benchmark-relative compounded return, reported with maximum drawdown | Volatility, Sharpe/Sortino, expected shortfall, turnover, exposure, cost stress, seed/fold dispersion |
| Simulator or RL mechanics | Reproducibility, state/action timing, reward arithmetic, constraint adherence, and performance against simple policies over matched seeds | Median and lower-tail net CAGR, drawdown, expected shortfall, turnover, sensitivity to simulator parameters |

For RL, the gym's `log(1 + net_return)` reward is a numerically stable compounding objective with some aversion to large losses; it is not a drawdown constraint and does not replace portfolio reporting. A discount factor below one further changes the objective: it prioritizes nearer log returns over later ones, so it no longer equals terminal log wealth. Record gamma and interpret reward separately from net CAGR, benchmark-relative wealth, and drawdown. A policy is not preferred solely because it has the largest mean reward or median Sharpe. Compare matched paths and report paired seed-level uncertainty for policy differences, 10th/50th/90th percentile risk and return outcomes, 1×/2×/4× costs, and any risk-limit breaches. For historical studies, resample at the independent unit (for example issuer/event clusters), not individual daily rows. This portfolio has no universal numeric hurdle that turns a backtest into proof of an edge; evidence must survive its preregistered final period and sensitivity checks.

## Primary metrics

| Measure | Definition | Why it belongs |
| --- | --- | --- |
| **Observation count** | Number of aligned periodic strategy/benchmark return observations used in the score | Makes the estimate's sample size visible; event studies must additionally report independent event and issuer counts |
| **Net CAGR** | `(ending wealth / starting wealth) ** (periods_per_year / observations) - 1`, after modeled costs | Describes compounded growth at the portfolio level |
| **Benchmark-relative compounded return** | `(strategy ending wealth / benchmark ending wealth) - 1`, using returns aligned on the same dates | Measures relative compounded wealth; unlike arithmetic return subtraction, it respects compounding |
| **Annualized volatility** | Sample standard deviation of periodic net returns times `sqrt(periods_per_year)` | Shows return variability that a growth number hides |
| **Sharpe ratio** | Mean periodic excess return divided by its sample standard deviation, annualized under the conventional square-root rule | Summarizes total volatility per unit of excess return |
| **Maximum drawdown** | Lowest peak-to-trough decline in the wealth curve, including starting capital | Makes path-dependent loss visible |
| **Annualized turnover** | Sum of absolute changes in portfolio weight, scaled to a year | Shows how much trading the return required |
| **Cost sensitivity** | Re-run the same frozen policy under base, 2×, and 4× per-unit transaction costs | Reveals whether the result relies on optimistic execution |
| **Catalyst-window downside** | Report every event return, event count, worst event, and a clearly named tail estimate | Shows the gap-loss exposure that daily volatility can understate |

Sharpe in this implementation assumes the supplied annual risk-free rate is converted to a per-period rate, defaults to zero, and uses conventional square-root annualization. Serial correlation can make that annualized estimate materially misleading; report the periodic return series, sampling frequency, and autocorrelation diagnostics with it. The square-root rule is a convention, not a claim that daily strategy returns are independent. See [Lo, “The Statistics of Sharpe Ratios”](https://traders.berkeley.edu/papers/The-Statistics-of-Sharpe-Ratios.pdf).

## Useful secondary measures

- **Sortino ratio:** excess return divided by downside deviation relative to a declared target. Here the default target is the risk-free return for each period.
- **Calmar ratio:** annualized net return divided by the absolute maximum drawdown. It is interpretable only with the drawdown period and track record length.
- **Information ratio:** mean periodic active return divided by tracking error, annualized, against the explicitly named benchmark.
- **Total return and benchmark-relative return:** disclose the observed-period compounded return, benchmark compounded return, relative wealth ratio, and the separate ending-wealth difference on identical dates. The ratio and wealth difference answer different questions and should not share one label.
- **Brier score and log loss:** for event downside probabilities, report both proper scoring rules against a training-fold base-rate forecast. Lower is better; include the event rate and five-bin development reliability table (`calibration.csv`) because a score can move with prevalence. The final chronological holdout stays out of the calibration artifact until a separately frozen final evaluation.
- **ROC AUC:** use as a ranking diagnostic only when the evaluation fold contains both outcomes. It does not assess probability calibration and is unstable with few independent events.

These summaries do not replace confidence intervals, fold-by-fold results, regime analysis, or costs. Sharpe, Sortino, and information ratio are estimates from a finite sample; do not use a universal threshold as a hiring badge or deployment gate.

The implementation's **5% historical VaR** is the empirical 5th-percentile periodic return; **5% expected shortfall** is the mean return in the worst `ceil(0.05 × n)` observations. Both are reported as returns (a negative number denotes loss). At small sample sizes the tail estimate is highly discrete; event-study work should additionally show every event return, sample count, uncertainty interval, and worst single event. An event tail can be sparse even when the daily return series is long.

For catalyst studies, keep two quantities separate: (1) **unconditional catalyst move risk**, computed from realized issuer event returns regardless of a policy's position, and (2) **policy catalyst loss**, computed from that policy's net return on event sessions. A cash strategy's zero event-session portfolio return is not evidence that issuer catalyst risk was zero. In the synthetic gym report, `catalyst_unconditional_expected_shortfall_95` describes underlying issuer moves; `catalyst_policy_net_expected_shortfall_95` describes the strategy after exposure and costs. The report also carries the event count and worst event return so the coarse 5% tail cannot hide a small denominator.

## What counts as a credible portfolio result

1. Freeze the hypothesis and candidate-selection process before opening the final chronological holdout.
2. Report net results on the untouched period and on each walk-forward fold, not only a pooled headline.
3. Compare cash, buy-and-hold, and a transparent strategy with the same market clock and costs.
4. Publish turnover and the 1×/2×/4× cost stress. Include any capacity or fill assumptions.
5. Record the number of variants tried. A single holdout does not erase selection bias when many strategies were searched; see the research on [probability of backtest overfitting](https://escholarship.org/uc/item/4w1110bb).
6. Preserve failed experiments and report how sensitive the result is to seeds, windows, and market regimes.

No historical strategy return or validated catalyst-risk model is currently claimed. The RL report uses a synthetic catalyst generator to exercise the simulator and reporting pipeline only. Historical event records and price data must be analyzed as a separate, versioned study.

The Python [`portfolio_backtest`](https://github.com/CastaliaInstitute/quant/blob/main/src/quantlab/portfolio.py) takes aligned asset-return and target-weight panels, treats each target as known at that row's close, and applies it to the next return row. It charges proportional cost on the sum of absolute position changes, keeps the remaining capital in cash, and rejects missing returns for held assets. Cash earns zero unless the caller supplies an aligned cash-return series. [`portfolio_cost_sensitivity`](https://github.com/CastaliaInstitute/quant/blob/main/src/quantlab/portfolio.py) replays the same frozen target weights at 1×/2×/4× costs and reports the scorecard above. The functions do not fit risk estimates or signals; use chronological, training-only inputs before reporting empirical metrics.
