# Quant. Experiment Log

This log preserves both superseded policy experiments and the current biotech catalyst simulator. Archived outputs remain available so a changed research domain does not erase earlier evidence.

## RL-001 · Generic regime gym · 300 training episodes · superseded

- Configuration: original generator and policy output is preserved as <a href="../_static/rl-generic-simulation-archive.json">rl-generic-simulation-archive.json</a>; training seed 17; evaluation seeds 10,000–10,059; 252 sessions; 5 bps per unit turnover.
- Outcome: the tabular learner's median path was all cash. Buy-and-hold median CAGR was 2.77%; trend-rule median CAGR was −3.43% with 51.0× annualized turnover.
- Interpretation: the learned policy did not demonstrate an advantage in the generic toy environment. This is not a market result.

## RL-002 · Generic-gym training-budget follow-up · 1,000 episodes · exploratory

- Purpose: inspect whether the all-cash median in RL-001 was only a small training budget.
- Configuration: same generator and evaluation seed block 10,000–10,059 as RL-001.
- Outcome: median evaluation remained all cash. This follow-up reused the first evaluation paths and was post hoc; that seed block must not be treated as a fresh holdout.

## RL-003 · Biotech catalyst gym with direction-linked outcomes · superseded

- Configuration: <a href="../_static/rl-simulation-legacy-linked-outcomes.json">archived report</a>, training seed 17; evaluation seeds 10,000–10,059; 252 sessions; 10 bps per unit turnover; 36 state bins; Phase II/III toy readouts every 63 sessions.
- Comparators: cash, long buy-and-hold, trailing-momentum trend, a five-session pre-catalyst exit rule, and tabular Q-learning on matched paths.
- Limitation: the generator made clinical success select a positive market gap and failure select a negative gap. This unrealistic linkage is retained in the archived report so the model change is traceable.

## RL-004 · Frozen-policy stress of direction-linked outcomes · superseded

- Configuration: <a href="../_static/rl-stress-legacy-linked-outcomes.json">archived report</a>; one Q table trained on base assumptions and evaluated unchanged across a shared seed block under success-rate, failure-gap, event-noise, and transaction-cost stresses.
- Comparators: cash, buy-and-hold, trend, pre-catalyst exit, and the frozen Q learner.
- Limitation: the stress study shares the direction-linked outcome assumption described in RL-003.

## RL-005 · Separate event outcomes from market reactions · superseded

- Model change: phase-specific event outcomes and stock reactions have separate random draws. This corrected the earlier direction-linked simulator. Positive market reactions can follow suspension; negative reactions can follow advancement. The action policy never observes the event outcome before the market return is realized.
- Limitation: its uncalibrated phase-outcome settings were replaced in RL-007; that intermediate report was not retained as a separate artifact. The earlier direction-linked model remains archived in RL-003.

## RL-006 · Frozen-policy market-response stress · rerun under RL-007 prior

- Configuration: <a href="../_static/rl-stress.json">rl-stress.json</a>; one Q table is trained on base assumptions and evaluated unchanged under advancement-rate, adverse-gap, market-reaction, event-noise, and cost stresses. The current base uses the published advancement priors recorded in RL-007.
- Outcome: the Q policy remains at zero median catalyst exposure and has −5.61% median CAGR in the synthetic base scenario. Buy-and-hold median CAGR ranges from −5.58% to −33.37% across the clinical and market stresses. These are simulator diagnostics, not empirical robustness evidence.

## RL-007 · Literature-informed phase-transition prior

- Configuration: current `config/biopharma_rl_synthetic.json` uses Phase II 28.9% and Phase III 57.8% program-advancement priors, based on published all-indication phase-transition data for 2011–2020 (BIO/Informa/QLS; transition counts 4,933 and 1,928 respectively). The current report is <a href="../_static/rl-simulation.json">rl-simulation.json</a>.
- Semantics: advancement to the next development stage is not equivalent to an individual trial meeting its prespecified primary endpoint. The selected CTO human-label subset is not used as a population prior.
- Result: across 60 synthetic paths, the median Q policy CAGR is −2.28%, benchmark-relative compounded return is −11.07%, and max drawdown is −10.99%. It holds exposure on 11.1% of sessions and 0% of catalyst sessions. Market-reaction probabilities, return-gap sizes, and ordinary daily returns remain synthetic and uncalibrated; this study does not estimate market returns.

## RL-008 · Paired policy uncertainty under the synthetic generator

- Method: regenerated RL-007 with 10,000 paired bootstrap resamples of the 60 shared evaluation episode seeds. The frozen Q policy is compared with cash, buy-and-hold, trend, and pre-catalyst exit using annualized return and benchmark-relative compounded-wealth differences.
- Result: mean Q-minus-baseline relative-wealth differences are +3.6 percentage points vs buy-and-hold (95% interval −11.6 to +16.8), +7.5 points vs trend (−3.5 to +17.6), and −3.3 points vs pre-catalyst exit (−12.2 to +5.2). All intervals include zero.
- Interpretation: this quantifies finite-seed variability conditional on one fixed synthetic generator and one trained policy. It excludes training-policy uncertainty and cannot establish a historical-market advantage. The paired values and deterministic bootstrap seeds are in <a href="../_static/rl-simulation.json">the versioned report</a>.

## RL-009 · Four-times transaction-cost stress

- Method: extended the RL-006 frozen-policy stress ladder from 1×/2× to 1×/2×/4× transaction costs, retrained once on base assumptions, and evaluated the same 60 seed paths without retuning.
- Result: at 4× costs, median Q-policy CAGR is −11.85% and benchmark-relative compounded wealth is −16.43%, versus −5.61% and −10.49% at base costs; median annual turnover is 18× and event-session exposure remains 0%. Buy-and-hold median CAGR is −8.97% at 4× costs.
- Interpretation: cost drag materially worsens this policy's synthetic result, and its 4× relative-wealth median is numerically close to buy-and-hold's (−16.39%). No paired uncertainty interval is estimated for this cross-scenario stress. This is a cost-mechanics diagnostic in an uncalibrated generator, not historical execution evidence. Results and scenario hashes are in <a href="../_static/rl-stress.json">rl-stress.json</a>.

## Next study: historical event-risk panel

The current historical data artifact is a nine-disclosure source-lineage fixture spanning vaccines, Alzheimer's, asthma, and oncology. It remains tiny and clustered, with several date-only catalyst times, so it cannot support fitting or a stable return estimate. The next research record should be opened only after adding a wider trial/disclosure cohort, point-in-time event features, a licensed OHLCV file, inactive/delisted issuers, and a preregistered chronological evaluation plan. Preserve every inclusion rule and data-source revision.

## Data audit · CTO 2020–2024 human-label subset

- Source: pinned MIT-licensed CTO repository revision `6b080abb5a510e8a6573085f4b843e08ac3b6204`; source-file SHA-256 and aggregate schema/coverage are recorded in <a href="../_static/cto-human-labels-audit.json">cto-human-labels-audit.json</a>.
- Scope observed: 11,012 unique trial rows with phases, status, registry dates, completion year, and binary labels.
- Disposition: benchmark/leakage audit only. The forbidden rule “current status is COMPLETED ⇒ label 1” reaches 97.05% accuracy because status is post-outcome and overlaps the target construction. Current fields are not treated as pre-outcome predictors; label prevalence is not a population phase-success estimate, and labels do not enter the stock-return target or synthetic RL transition probabilities. See the [CTO audit](cto-audit.md) and <a href="../_static/cto-human-labels-audit.json">aggregate report</a>.
- Next use: if the clinical progression benchmark is pursued, retrieve trial-history versions, preregister outcome-time and feature cutoffs, and use temporal/sponsor-aware validation. For price-reaction calibration, acquire a separate timestamped catalyst and licensed-return panel.
