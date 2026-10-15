# RL Study 005: Separate Clinical Outcomes from Market Reactions

```{raw} html
<p class="castalia-kicker">SIMULATOR DIAGNOSTIC · NOT A HISTORICAL RESULT</p>
```

This executable simulator exercise trains a tabular Q learner in a seeded, single-issuer catalyst gym. It compares the learned policy with cash, buy-and-hold, a five-day trend rule, and a pre-catalyst exit heuristic on matched synthetic paths. This revision separates program advancement from the stock's response to the readout. The previous direction-linked synthetic model is preserved as <a href="../_static/rl-simulation-legacy-linked-outcomes.json">a superseded report</a>.

## Environment and policy

- **Observation:** five-session issuer momentum, trailing 20-session volatility, time until the next scheduled readout, and its known Phase II/III category. Continuous features are discretized into 36 tabular states.
- **Event timing for empirical replay:** future event schedules may enter the observation only when their dates and phase were documented before the decision cutoff. `scheduled_event_phases` controls observable timing; `realized_event_phases` records event labels for post-action reporting. Historical disclosure dates belong only in the realized labels unless a dated pre-event schedule source proves they were known in advance. The legacy `event_phases` option still supplies both arrays for existing synthetic forks.
- **Action:** 0 = cash; 1 = fully invested long.
- **Transition:** the action earns the current session return after observing only prior returns. The phase and scheduled catalyst distance are observable; the clinical outcome and market reaction remain hidden until the return is realized. A position change costs 10 basis points per unit turnover.
- **Reward:** log of one plus net periodic return. Reporting metrics use net simple returns.
- **Objective distinction:** with `γ = 0.98`, Q-learning optimizes the discounted sum `Σ γᵏ log(1 + net_returnₖ)`, not undiscounted terminal log wealth or net CAGR. At the default discount, a reward about 34 sessions ahead has half the weight of an immediate one. The report records the discount and its half-life; CAGR, relative wealth, and drawdown remain evaluation metrics, not the learner's optimized objective.
- **Evaluation:** 60 independent episode seeds beginning at 10,000, paired across policies. This evaluation block has not been reused for policy search.
- **Scorecard:** net CAGR, volatility, Sharpe, Sortino, maximum drawdown, VaR / expected shortfall, turnover, total costs, invested exposure, and catalyst-specific losses. Report distributions across seeds, not only the median.
- **Learner:** 36-state, two-action tabular Q-learning. The report JSON records the exact learning rate, discount, seeds, Q values, decoded greedy action by state, and how often each action was chosen in each training state. Visit counts include exploration actions and help flag preferences learned from sparse coverage.
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
| Q learner | −2.28% [−12.98%, 12.38%] | −11.07% [−31.81%, 26.03%] | −0.14 | −10.99% | 0% | 20.0× |

The Q learner's median catalyst exposure is 0%, with median overall exposure of 11.1%; its policy is not fully in cash. The pre-catalyst rule exits during the final five sessions, including event sessions; its threshold adapts to the configured catalyst cadence. None of these outcomes support a claim about historical biotech stocks. Changing advancement, reaction, and gap assumptions could reverse the ranking. Each episode has only three catalyst sessions, so its within-episode 5% tail reduces to the worst event; the report publishes the per-episode event denominator and the across-seed distribution. The unconditional issuer-gap estimate is separate from the policy's event-session net returns.

The report also computes **paired bootstrap intervals** for the Q learner's per-seed annualized-return and benchmark-relative-wealth differences against each baseline. Across the 60 matched seeds, the mean relative-wealth difference was +3.6 percentage points versus buy-and-hold (95% paired-bootstrap interval −11.6 to +16.8 points), +7.5 points versus trend (−3.5 to +17.6), and −3.3 points versus the pre-catalyst exit rule (−12.2 to +5.2). Each interval spans zero. These intervals quantify seed variation under this fixed synthetic generator and frozen trained policy; they do not include training-seed uncertainty and are not inference about historical market returns. Full comparisons and bootstrap seeds are stored in the report JSON.

### Training-seed robustness

Because the single-policy intervals above condition on one Q table, a second diagnostic independently trains 10 Q tables (training seeds 17, 1,017, …, 9,017) and evaluates every table on the same 60 episode seeds. A two-way bootstrap resamples training-seed rows and shared evaluation-seed columns, so it includes both sources of variation under the fixed simulator. The <a href="../_static/rl-training-robustness.json">crossed-seed report</a> gives the Q-minus-trend benchmark-relative-wealth difference as +2.8 percentage points, with a 95% interval of −6.9 to +12.0 points; the Q-minus-buy-and-hold interval is −17.3 to +13.5 points. Both include zero.

The greedy Q policy chose long in a median of only 1 of 36 states across training runs (range 0–3); median evaluation exposure was 0.4%, and catalyst exposure was 0%. Its small drawdowns therefore reflect an almost-cash policy, not a demonstrated return advantage. The bootstrap has only 10 training-seed clusters and is an exploratory simulator diagnostic, not a market confidence interval.

### Why does the agent choose cash?

The <a href="../_static/rl-reward-incentive-audit.json">reward-incentive audit</a> computes expected log rewards directly from the configured return distributions using Gauss-Hermite quadrature. An ordinary long session has assumed arithmetic drift of 2.38 bps and volatility of 2.52%; its expected log reward is −0.0000813, while cash earns zero. At that volatility, the arithmetic mean needed for zero expected log reward is 3.19 bps per session. The configured event mixtures also have negative expected log reward in both Phase II (−6.65%) and Phase III (−8.93%) event sessions. A 252-session buy-and-hold path with three scheduled events therefore has an expected geometric wealth change of −22.51% after its entry cost, versus 0% for cash, under these synthetic assumptions.

All 36 states and 69–72 of 72 state-action pairs were visited across the ten training runs, though these coverage counts do not show balanced visitation. The cash-heavy policy is consistent with the configured negative geometric-growth incentives, not proof of a market signal. This audit makes the assumption effect inspectable; only calibration from point-in-time historical returns can determine whether those incentives resemble biotech markets.

The default run visited all 36 states across 75,600 training decisions. Its greedy action is cash in 34 states and long in 2; the Q learner's median out-of-sample exposure on catalyst sessions is 0%. The JSON's `learned_policy_by_state` decodes each greedy action into momentum, volatility, catalyst proximity, and phase, and gives separate cash/long training visit counts. A Q preference with few visits is weakly informed even inside this simulator; a well-visited preference is still only a result under the synthetic generator.

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
python scripts/run_rl_study.py --learning-rate 0.12 --discount 0.98
```

Source: [`simulation.py`](https://github.com/CastaliaInstitute/quant/blob/main/src/quantlab/simulation.py), [`rl_study.py`](https://github.com/CastaliaInstitute/quant/blob/main/src/quantlab/rl_study.py), and [`run_rl_study.py`](https://github.com/CastaliaInstitute/quant/blob/main/scripts/run_rl_study.py).

## Limits and next experiments

Episodes are independent draws from the same synthetic generator family used in training, not new market regimes or historical out-of-sample data. The environment's scheduled catalyst frequency, clinical outcome probabilities, conditional stock-reaction probabilities, gap returns, broad-market correlation, and cost assumptions are not calibrated. The small tabular agent's result is sensitive to how those assumptions are encoded. The pre-catalyst state bin adapts to the configured catalyst interval. The multi-training-seed bootstrap currently uses only 10 trained policies, so its interval is exploratory and should not be interpreted as a precise estimate of algorithm variability.

The research ladder is:

1. **Mechanics gym (current):** verify state/action timing, costs, reward, and deterministic reporting with explicitly synthetic outcomes.
2. **Calibrated simulator:** estimate distributions from historical, point-in-time event panels; preserve uncertainty and allow stress scenarios outside the fitted range. Fit simulator parameters on training dates only.
3. **Historical replay:** train policies on past data and evaluate walk-forward on later event clusters/issuers. Keep a final chronological holdout untouched, compare rule-based baselines, and report results by issuer, phase, and regime.
4. **Paper execution:** only after replay survives cost, timestamp, and risk review; use a broker sandbox with kill switches and no live capital.

The next empirical step is the [biopharma source and event panel](../data-sources.md). The first public-event cohort is clustered in the 2020–2021 COVID-19 vaccine program and is too small for model training. Expand the cohort, acquire point-in-time trial versions and licensed prices, and estimate descriptive event risk first. Then use empirical replay in a gym, with disjoint chronological train/validation/test data and an untouched final period. Never random-split event rows: multiple readouts from one issuer, trial program, or market episode are dependent.
