# RL Study 006: Stress the Frozen Catalyst Policy

```{raw} html
<p class="castalia-kicker">COUNTERFACTUAL ASSUMPTIONS · NO RETUNING</p>
```

This study freezes one Q table trained on the base configuration, then evaluates it under one-factor-at-a-time changes to program-advancement rates, negative market gaps, positive price response after advancement, event noise, and trading costs. Advancement outcomes and market reactions are separate draws in this simulator revision. Cash, buy-and-hold, trend, and pre-catalyst-exit policies use matched paths in each scenario.

This is a robustness diagnostic for simulator research. The stress parameters are hypothetical, not estimates from clinical-trial history or market prices. No policy is retuned from the stress results, and these runs cannot demonstrate historical or future profitability.

## Scorecard

The JSON artifact reports median and 10th/90th percentile results across episode seeds for net CAGR, benchmark-relative compounded return, maximum drawdown, expected shortfall, turnover, transaction cost, general exposure, catalyst-session exposure, program advancement, and market response conditional on outcome. Scenario definitions and resolved parameter values are stored with SHA-256 hashes.

<a href="../_static/rl-stress.json">Open the reproducible stress report</a>.

For the frozen Q learner, the default 60-seed run produced these median outcomes:

| Evaluation scenario | Q net CAGR | Q relative wealth | Q max drawdown | Buy-and-hold net CAGR |
| --- | ---: | ---: | ---: | ---: |
| Base assumptions | −5.61% | −10.49% | −13.44% | −8.70% |
| Program-advancement probabilities −10 percentage points | −5.61% | −10.49% | −13.44% | −14.91% |
| Program-advancement probabilities +10 percentage points | −5.61% | −10.49% | −13.44% | −5.58% |
| Negative market gaps 1.5× more severe | −5.61% | −10.49% | −13.44% | −33.37% |
| Positive reaction after advancement −15 percentage points | −5.61% | −10.49% | −13.44% | −18.81% |
| Event residual noise 2× | −5.61% | −10.49% | −12.89% | −9.21% |
| Transaction costs 2× | −7.44% | −12.43% | −14.40% | −8.79% |

Relative wealth is versus the matched broad-market path. Across these scenarios the Q learner's median catalyst-session exposure remains 0%; therefore the frozen policy barely responds to changes in advancement or market-reaction assumptions. The materially changing buy-and-hold results confirm that the stress paths do alter issuer returns. Zero event exposure is a simulator behavior diagnostic, not evidence that the policy found a real risk-adjusted edge. The full report includes cash and all rule-based comparators, percentiles, and tail-risk measures.

## Reproduce

From the repository root:

```bash
python scripts/run_rl_stress.py
python scripts/run_rl_stress.py --evaluation-runs 120 --evaluation-seed 20000
```

The Q learner trains once using the base assumptions. All stress scenarios reuse the independent evaluation seed block; comparisons across scenarios are counterfactuals under the same seeded random stream. They are not independent holdout replications. The base evaluation block from RL-005 is separate. The earlier direction-linked stress experiment is preserved in <a href="../_static/rl-stress-legacy-linked-outcomes.json">an archived report</a>.

## Interpretation

Read the Q policy beside all four baselines and inspect the scenario changes before comparing headline medians. A policy that loses its relative performance under a modest cost, advancement-outcome, or market-reaction shift has fragile simulator behavior. A stable ranking under these selected stresses would still say only that the policy is less sensitive to these particular assumptions; it would not support a claim about actual biotech securities.

The next evidence step remains historical replay using a broader point-in-time trial/event panel and licensed prices. Historical calibration should be estimated only from training windows, with out-of-range stress values preserved rather than clipped to make the policy look stable.
