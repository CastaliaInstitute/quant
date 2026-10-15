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

## RL-006 · Frozen-policy market-response stress · rerun under RL-007 prior · superseded by RL-012

- Configuration: archived <a href="../_static/rl-stress-gamma098-archive.json">gamma-0.98 report</a>; one Q table is trained on base assumptions and evaluated unchanged under advancement-rate, adverse-gap, market-reaction, event-noise, and cost stresses. The current base uses the published advancement priors recorded in RL-007.
- Outcome: the Q policy remains at zero median catalyst exposure and has −5.61% median CAGR in the synthetic base scenario. Buy-and-hold median CAGR ranges from −5.58% to −33.37% across the clinical and market stresses. These are simulator diagnostics, not empirical robustness evidence.

## RL-007 · Literature-informed phase-transition prior

- Configuration: current `config/biopharma_rl_synthetic.json` uses Phase II 28.9% and Phase III 57.8% program-advancement priors, based on published all-indication phase-transition data for 2011–2020 (BIO/Informa/QLS; transition counts 4,933 and 1,928 respectively). Its gamma-0.98 report is preserved in <a href="../_static/rl-simulation-gamma098-archive.json">the archive</a>; RL-012 gives the current report.
- Semantics: advancement to the next development stage is not equivalent to an individual trial meeting its prespecified primary endpoint. The selected CTO human-label subset is not used as a population prior.
- Result: across 60 synthetic paths, the median Q policy CAGR is −2.28%, benchmark-relative compounded return is −11.07%, and max drawdown is −10.99%. It holds exposure on 11.1% of sessions and 0% of catalyst sessions. Market-reaction probabilities, return-gap sizes, and ordinary daily returns remain synthetic and uncalibrated; this study does not estimate market returns.

## RL-008 · Paired policy uncertainty under the synthetic generator

- Method: regenerated RL-007 under gamma 0.98 with 10,000 paired bootstrap resamples of the 60 shared evaluation episode seeds. The frozen Q policy is compared with cash, buy-and-hold, trend, and pre-catalyst exit using annualized return and benchmark-relative compounded-wealth differences.
- Result: mean Q-minus-baseline relative-wealth differences are +3.6 percentage points vs buy-and-hold (95% interval −11.6 to +16.8), +7.5 points vs trend (−3.5 to +17.6), and −3.3 points vs pre-catalyst exit (−12.2 to +5.2). All intervals include zero.
- Interpretation: this quantifies finite-seed variability conditional on one fixed synthetic generator and one trained policy. It excludes training-policy uncertainty and cannot establish a historical-market advantage. The paired values and deterministic bootstrap seeds are preserved in <a href="../_static/rl-simulation-gamma098-archive.json">the gamma-0.98 archive</a>.

## RL-009 · Four-times transaction-cost stress

- Method: extended the RL-006 frozen-policy stress ladder from 1×/2× to 1×/2×/4× transaction costs, retrained once on base assumptions, and evaluated the same 60 seed paths without retuning under gamma 0.98.
- Result: at 4× costs, median Q-policy CAGR is −11.85% and benchmark-relative compounded wealth is −16.43%, versus −5.61% and −10.49% at base costs; median annual turnover is 18× and event-session exposure remains 0%. Buy-and-hold median CAGR is −8.97% at 4× costs.
- Interpretation: cost drag materially worsens this policy's synthetic result, and its 4× relative-wealth median is numerically close to buy-and-hold's (−16.39%). No paired uncertainty interval is estimated for this cross-scenario stress. This is a cost-mechanics diagnostic in an uncalibrated generator, not historical execution evidence. Results and scenario hashes are preserved in <a href="../_static/rl-stress-gamma098-archive.json">the gamma-0.98 archive</a>.

## RL-010 · Crossed training/evaluation seed robustness

- Method: independently train 10 Q tables (seeds 17 through 9,017 at stride 1,000) under gamma 0.98, evaluate each on the same 60 episode seeds starting at 30,000, and bootstrap the training-seed rows and evaluation-seed columns as crossed clusters.
- Result: Q-minus-trend benchmark-relative wealth has a +2.8 percentage-point mean difference with 95% two-way bootstrap interval −6.9 to +12.0 points; the Q-minus-buy-and-hold interval is −17.3 to +13.5 points. Both include zero. Across the 10 learned tables, greedy long actions occur in a median of 1/36 states (range 0–3); median evaluation exposure is 0.4%, with zero catalyst-session exposure.
- Interpretation: the learner mostly collapses to cash in this generator. Its modest drawdown is not evidence of alpha, and its interval includes both training and evaluation-seed variation but is exploratory with only 10 training policies. See the archived <a href="../_static/rl-training-robustness-gamma098-archive.json">gamma-0.98 report</a>.

## RL-011 · Reward-incentive attribution

- Method: use 80-node Gauss-Hermite quadrature on the configured ordinary-session normal return and each phase/outcome/reaction event mixture; retain the configured log-net-return reward and 10 bps entry cost. Cross-check training coverage using the RL-010 report.
- Result: ordinary sessions have 2.375 bps arithmetic drift and 2.524% volatility; expected long log reward is −0.0000813 versus zero for cash. Zero log reward requires 3.188 bps arithmetic drift at that volatility. Expected log reward is −6.65% per Phase II event and −8.93% per Phase III event. The episode-level buy-and-hold geometric wealth change is −22.51% after entry cost; all-cash is 0%.
- Interpretation: observed cash preference is consistent with the synthetic reward economics. The audit's gamma-0.98 training-coverage snapshot reports the earlier 36-state design; it is preserved in <a href="../_static/rl-reward-incentive-audit-gamma098-archive.json">the archive</a>. It explains the configured toy environment, not biotech securities.

## RL-012 · Align finite-horizon reward with terminal wealth · superseded by RL-013

- Decision: use `gamma=1` for the finite-horizon long-or-cash gym. Summed log net returns then equal log terminal wealth, so expected reward directly targets expected compounded growth. Drawdown, tail loss, catalyst exposure, and turnover remain separate evaluation gates; they are not optimized or constrained by the scalar reward. Lower gamma remains a configurable time-preference sensitivity.
- Reproducibility: regenerated the 300-episode study, 10-training-seed crossed bootstrap, and frozen-policy stress report from the checked-in assumptions. The former gamma-0.98 artifacts are archived above.
- Result: the Q learner's median net CAGR is 0.00%, median benchmark-relative wealth −7.73%, median maximum drawdown −0.10%, and median overall exposure 0.4%. Its paired relative-wealth intervals include zero against cash, buy-and-hold, trend, and pre-catalyst exit. Across 10 independent training runs, the Q-minus-trend relative-wealth difference is +2.2 percentage points (95% crossed-bootstrap interval −7.4 to +11.5); the Q-minus-buy-and-hold interval is −17.8 to +12.8. The learned policy remains nearly cash under the current synthetic assumptions.
- Interpretation: gamma 1 corrects the objective mismatch but does not create evidence of a biotech trading edge. Historical return claims remain gated on a larger point-in-time trial-event cohort and licensed price data. Its gamma-1 but non-Markov state results are preserved in the <a href="../_static/rl-simulation-gamma1-pre-markov-archive.json">study</a>, <a href="../_static/rl-training-robustness-gamma1-pre-markov-archive.json">crossed-seed</a>, and <a href="../_static/rl-stress-gamma1-pre-markov-archive.json">stress</a> archives.

## RL-013 · Make the finite-horizon policy state Markov

- Model correction: include remaining episode horizon and current position in the observation. The former lets the finite-horizon policy adapt to time remaining; the latter makes turnover-cost consequences observable before action selection. This expands the discretized state space from 36 to 288 states while retaining the finite-horizon `gamma=1` terminal-log-wealth objective.
- Protocol: regenerate the primary study, independent training-seed robustness panel, and frozen-policy market/cost stresses from the checked-in synthetic assumptions. Preserve the gamma-0.98 and gamma-1 pre-Markov reports as archives; report state-action coverage because the larger table increases sparsity.
- Result: under the one-table evaluation, median Q net CAGR is 0.00% [−12.62%, +8.87%], median relative wealth is −9.82% [−25.97%, +11.32%], median drawdown −6.13%, turnover 21×, and overall exposure 4.2%; event exposure remains zero. The paired Q-minus-cash relative-wealth interval is −4.1 to −0.1 points in this synthetic sample. In the crossed 10-training-seed report, Q-minus-trend is +2.5 points (95% interval −7.1 to +11.9) and Q-minus-buy-and-hold is −1.7 points (−17.6 to +13.4). Training covers 220–226/288 states and 409–419/576 state/action pairs; unseen ties default to cash.
- Interpretation gate: these remain simulator diagnostics only. The learner is sparse and its cash-relative result is unfavorable under the configured return process. It must be calibrated on point-in-time biotech events and beat cash plus transparent portfolio baselines on historical data with licensed prices before any market-skill claim.

## Next study: historical event-risk panel

The current historical data artifact is a nine-disclosure source-lineage fixture spanning vaccines, Alzheimer's, asthma, and oncology. It remains tiny and clustered, with several date-only catalyst times, so it cannot support fitting or a stable return estimate. The next research record should be opened only after adding a wider trial/disclosure cohort, point-in-time event features, a licensed OHLCV file, inactive/delisted issuers, and a preregistered chronological evaluation plan. Preserve every inclusion rule and data-source revision.

## Data audit · CTO 2020–2024 human-label subset

- Source: pinned MIT-licensed CTO repository revision `6b080abb5a510e8a6573085f4b843e08ac3b6204`; source-file SHA-256 and aggregate schema/coverage are recorded in <a href="../_static/cto-human-labels-audit.json">cto-human-labels-audit.json</a>.
- Scope observed: 11,012 unique trial rows with phases, status, registry dates, completion year, and binary labels.
- Disposition: benchmark/leakage audit only. The forbidden rule “current status is COMPLETED ⇒ label 1” reaches 97.05% accuracy because status is post-outcome and overlaps the target construction. Current fields are not treated as pre-outcome predictors; label prevalence is not a population phase-success estimate, and labels do not enter the stock-return target or synthetic RL transition probabilities. See the [CTO audit](cto-audit.md) and <a href="../_static/cto-human-labels-audit.json">aggregate report</a>.
- Next use: if the clinical progression benchmark is pursued, retrieve trial-history versions, preregister outcome-time and feature cutoffs, and use temporal/sponsor-aware validation. For price-reaction calibration, acquire a separate timestamped catalyst and licensed-return panel.
