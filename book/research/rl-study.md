# RL Study 005: Separate Clinical Outcomes from Market Reactions

```{raw} html
<p class="castalia-kicker">SIMULATOR DIAGNOSTIC · NOT A HISTORICAL RESULT</p>
```

This executable simulator exercise trains a tabular Q learner in a seeded, single-issuer catalyst gym. It compares the learned policy with cash, buy-and-hold, a five-day trend rule, and a pre-catalyst exit heuristic on matched synthetic paths. This revision separates program advancement from the stock's response to the readout. The previous direction-linked synthetic model is preserved as <a href="../_static/rl-simulation-legacy-linked-outcomes.json">a superseded report</a>.

## Environment and policy

- **Observation:** five-session issuer momentum, trailing 20-session volatility, time until the next scheduled readout, its known Phase II/III category, remaining episode horizon, and current position. The last two variables make the finite-horizon reward and turnover-cost transition observable. The tabular state space contains 288 combinations (36 market/catalyst states × 4 horizon bins × 2 position states); sparse state-action coverage is reported.
- **Event timing for empirical replay:** future event schedules may enter the observation only when their dates and phase were documented before the decision cutoff. `scheduled_event_phases` controls observable timing; `realized_event_phases` records event labels for post-action reporting. Historical disclosure dates belong only in the realized labels unless a dated pre-event schedule source proves they were known in advance. The legacy `event_phases` option still supplies both arrays for existing synthetic forks.
- **Action:** 0 = cash; 1 = fully invested long.
- **Transition:** the action earns the current session return after observing only prior returns. The phase and scheduled catalyst distance are observable; the clinical outcome and market reaction remain hidden until the return is realized. A position change costs 10 basis points per unit turnover.
- **Reward and objective:** log of one plus net periodic return. The finite-horizon default is `γ = 1`, so summed rewards equal log terminal wealth exactly; Q-learning therefore targets expected log compounded wealth. A fork may lower gamma as an explicit time-preference sensitivity, but then its reward no longer equals terminal log wealth. Reporting metrics use net simple returns.
- **Risk controls:** drawdown, expected shortfall, event exposure, and turnover remain separate evaluation gates. The current long-or-cash action space does not enforce pathwise drawdown or portfolio-level issuer/sector limits; those constraints must be represented in a future multi-asset environment before any empirical policy claim.
- **Evaluation:** 60 independent episode seeds beginning at 10,000, paired across policies. These are diagnostic draws from the same synthetic generator, not a historical-market holdout or evidence of regime generalization.
- **Scorecard:** net CAGR, volatility, Sharpe, Sortino, maximum drawdown, VaR / expected shortfall, turnover, total costs, invested exposure, and catalyst-specific losses. Report distributions across seeds, not only the median.
- **Learner:** 288-state, two-action tabular Q-learning. The report JSON records the exact learning rate, discount, seeds, Q values, decoded greedy action by state, and how often each action was chosen in each training state. Visit counts include exploration actions and help flag preferences learned from sparse coverage.
- **Evidence-informed clinical prior:** the Phase II / Phase III program-advancement settings (0.289 / 0.578) reflect published 2011–2020 all-disease phase-transition rates, not primary-endpoint success probabilities. The source population and limitations are described in the [evidence review](evidence-review.md). The simulator still samples separate program advancement and market response; a program can advance while its stock falls, or be suspended while its stock rises.
- **Synthetic market assumptions:** phase/outcome-conditional positive market-reaction probabilities, positive/negative gap sizes, market process, and costs are read from [`config/biopharma_rl_synthetic.json`](../../config/biopharma_rl_synthetic.json). These values remain illustrative and uncalibrated; no historical security-price panel was used. The report stores the resolved values and SHA-256 of the config.

The interface follows the [Gymnasium reset/step API](https://gymnasium.farama.org/api/env/) and its [custom-environment guide](https://gymnasium.farama.org/tutorials/gymnasium_basics/environment_creation/). The environment makes timing observable, but it is still too stylized to represent actual biotech issuer risk.

## Results

The report summarizes 300 training episodes and 60 matched 252-session evaluation paths. Results include net CAGR, benchmark-relative compounded return, volatility, Sharpe, drawdown, VaR / expected shortfall, turnover, time invested, and exposure during catalyst sessions. It separates **program advancement**, **issuer market response**, and **policy net return**. In the JSON, `clinical_success` is a legacy field name for Phase II-to-III or Phase III-to-NDA/BLA advancement, not primary-endpoint success. The pooled summary covers 180 synthetic readouts: 71 advancements and 109 suspensions; positive issuer returns occurred after 81.7% of advancements and 22.9% of suspensions. The phase outcome rates are based on published aggregate transitions; market reactions and returns are synthetic. A cash policy can avoid event loss while the issuer still experiences a gap. Values below are medians; return brackets show the 10th–90th percentile range. Relative wealth is strategy ending wealth divided by matched broad-market ending wealth, minus one. All values are simulator diagnostics and are reproduced in the versioned <a href="../_static/rl-simulation.json">rl-simulation.json</a>.

| Policy | Net CAGR | Relative wealth vs broad market | Sharpe | Max drawdown | Catalyst exposure | Annualized turnover |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Cash | 0.00% [0.00%, 0.00%] | −7.48% [−24.78%, 10.36%] | 0.00 | 0.00% | 0% | 0.0× |
| Buy-and-hold | −17.71% [−57.33%, 56.07%] | −23.39% [−60.23%, 50.42%] | 0.04 | −46.04% | 100% | 1.0× |
| Trend rule | −14.61% [−45.58%, 44.01%] | −20.97% [−52.45%, 29.60%] | −0.36 | −37.13% | 33% | 53.0× |
| Pre-catalyst exit | −9.57% [−35.26%, 52.08%] | −11.71% [−41.39%, 38.98%] | −0.08 | −35.71% | 0% | 7.0× |
| Q learner | 0.00% [−12.62%, 8.87%] | −9.82% [−25.97%, 11.32%] | 0.00 | −6.13% | 0% | 21.0× |

With γ=1 and horizon/position-aware states, the Q learner's median catalyst exposure is 0%, median total exposure is 4.2%, and median turnover is 21× annualized. The larger downside spread and turnover reflect the changed state representation; the policy remains unvalidated. In paired benchmark-relative wealth, it underperforms cash by 2.1 percentage points on average (95% paired-bootstrap interval −4.1 to −0.1) under this one synthetic generator. Intervals versus buy-and-hold, trend, and pre-catalyst exit all span zero. The pre-catalyst rule exits during the final five sessions, including event sessions; its threshold adapts to the configured catalyst cadence. None of these outcomes support a claim about historical biotech stocks. Changing advancement, reaction, and gap assumptions could reverse the ranking. Each episode has only three catalyst sessions, so its within-episode 5% tail reduces to the worst event; the report publishes the per-episode event denominator and the across-seed distribution. The unconditional issuer-gap estimate is separate from the policy's event-session net returns.

The report also computes **paired bootstrap intervals** for the Q learner's per-seed annualized-return and benchmark-relative-wealth differences against each baseline. Across the 60 matched seeds, mean relative-wealth differences were +2.3 percentage points versus buy-and-hold (95% paired-bootstrap interval −12.7 to +15.4 points), +6.2 points versus trend (−4.1 to +15.7), and −4.7 points versus the pre-catalyst exit rule (−13.6 to +3.8). These intervals span zero. The Q-minus-cash interval is −4.1 to −0.1 points in this synthetic seed block. These intervals quantify seed variation under this fixed synthetic generator and trained policy; they do not include training-seed uncertainty and are not inference about historical market returns. Full comparisons and bootstrap seeds are stored in the report JSON.

### Training-seed robustness

Because the single-policy intervals above condition on one Q table, a second diagnostic independently trains 10 Q tables (training seeds 17, 1,017, …, 9,017) and evaluates every table on the same separate 60 episode seeds beginning at 30,000. A two-way bootstrap resamples training-seed rows and shared evaluation-seed columns, so it includes both sources of variation under the fixed simulator. The <a href="../_static/rl-training-robustness.json">crossed-seed report</a> gives the Q-minus-trend benchmark-relative-wealth difference as +2.5 percentage points, with a 95% interval of −7.1 to +11.9 points; the Q-minus-buy-and-hold interval is −17.6 to +13.4 points. Both include zero.

The greedy Q policy chose long in a median of 15 of 288 states across training runs (range 7–20); median evaluation exposure was 0.8% (10th–90th percentile 0%–7.1%), and catalyst exposure was 0%. Each training run visited 220–226 states and 409–419 of 576 state/action pairs. Its results remain sensitive to sparse tabular coverage; the bootstrap has only 10 training-seed clusters and is an exploratory simulator diagnostic, not a market confidence interval.

### Why does the agent choose cash?

The <a href="../_static/rl-reward-incentive-audit.json">reward-incentive audit</a> computes expected log rewards directly from the configured return distributions using Gauss-Hermite quadrature. An ordinary long session has assumed arithmetic drift of 2.38 bps and volatility of 2.52%; its expected log reward is −0.0000813, while cash earns zero. At that volatility, the arithmetic mean needed for zero expected log reward is 3.19 bps per session. The configured event mixtures also have negative expected log reward in both Phase II (−6.65%) and Phase III (−8.93%) event sessions. A 252-session buy-and-hold path with three scheduled events therefore has an expected geometric wealth change of −22.51% after its entry cost, versus 0% for cash, under these synthetic assumptions.

Across the ten training runs, only 76%–78% of the 288 states and 71%–73% of the 576 state/action pairs were visited. Unvisited actions retain tied Q values and deterministic argmax selects cash, so coverage is a direct limitation on the learned policy. The cash-heavy behavior is consistent with the configured negative geometric-growth incentives, not proof of a market signal. This audit makes both assumption effects and state sparsity inspectable; only calibration from point-in-time historical returns can determine whether those incentives resemble biotech markets.

The default run visited 223 states and 413 of 576 state/action pairs across 75,600 training decisions. Its greedy action is long in 16 of the 288 encoded states, including unvisited states where Q values tie. The JSON's `learned_policy_by_state` decodes each greedy action into momentum, volatility, catalyst proximity, phase, episode horizon, and current position, with separate cash/long training visit counts. A Q preference with few visits is weakly informed even inside this simulator; a well-visited preference is still only a result under the synthetic generator.

## Reproduce

From the repository root:

```bash
python -m pip install -e '.[rl]'
python scripts/run_rl_study.py
python scripts/run_rl_training_robustness.py
python scripts/audit_rl_reward_incentives.py
# To tune a fork, copy and edit config/biopharma_rl_synthetic.json:
python scripts/run_rl_study.py --assumptions path/to/your-assumptions.json
# Learner hyperparameters are also explicit:
python scripts/run_rl_study.py --learning-rate 0.12 --discount 1.0
```

Source: [`simulation.py`](https://github.com/CastaliaInstitute/quant/blob/main/src/quantlab/simulation.py), [`rl_study.py`](https://github.com/CastaliaInstitute/quant/blob/main/src/quantlab/rl_study.py), and [`run_rl_study.py`](https://github.com/CastaliaInstitute/quant/blob/main/scripts/run_rl_study.py).

## Limits and next experiments

Episodes are independent draws from the same synthetic generator family used in training, not new market regimes or historical out-of-sample data. The environment's scheduled catalyst frequency, clinical outcome probabilities, conditional stock-reaction probabilities, gap returns, broad-market correlation, and cost assumptions are not calibrated. The small tabular agent's result is sensitive to how those assumptions are encoded. The pre-catalyst state bin adapts to the configured catalyst interval. The multi-training-seed bootstrap currently uses only 10 trained policies, so its interval is exploratory and should not be interpreted as a precise estimate of algorithm variability.

The research ladder is:

1. **Mechanics gym (current):** verify state/action timing, costs, reward, and deterministic reporting with explicitly synthetic outcomes.
2. **Calibrated simulator:** estimate distributions from historical, point-in-time event panels; preserve uncertainty and allow stress scenarios outside the fitted range. Fit simulator parameters on training dates only.
3. **Portfolio construction baselines:** before RL allocation, compare cash, equal-weight, and inverse-volatility portfolios across the eligible issuer universe. Add issuer/sector caps, a declared rebalance clock, and execution costs; report net CAGR, benchmark-relative wealth, maximum drawdown, turnover, exposure, and tail loss.
4. **Historical replay:** train policies on past data and evaluate walk-forward on later event clusters/issuers. Keep a final chronological holdout untouched, compare rule-based baselines, and report results by issuer, phase, and regime. Any future multi-asset RL action must obey the same exposure and turnover limits as its baselines.
5. **Paper execution:** only after replay survives cost, timestamp, and risk review; use a broker sandbox with kill switches and no live capital.

The next empirical step is the [biopharma source and event panel](../data-sources.md). The first public-event cohort is clustered in the 2020–2021 COVID-19 vaccine program and is too small for model training. Expand the cohort, acquire point-in-time trial versions and licensed prices, and estimate descriptive event risk first. Then use empirical replay in a gym, with disjoint chronological train/validation/test data and an untouched final period. Never random-split event rows: multiple readouts from one issuer, trial program, or market episode are dependent.

Run [`scripts/audit_rl_replay_readiness.py`](../../scripts/audit_rl_replay_readiness.py) to refresh the [replay-readiness audit](../_static/rl-replay-readiness.json). It checks adjusted prices for every event ticker plus SPY/XBI, unique event IDs, matched sessions and returns, issuer-quarter/calendar-quarter coverage, and minimum panel-event counts after a date-clustered 60/20/20 chronological split (defaults: 30/8/8 events, 10 issuers, and 10 calendar quarters). Duplicate events and rows with incomplete matching do not count as usable observations. The audit reports readiness only; it does not train a policy or estimate returns. The nine-event fixture should fail these gates.
