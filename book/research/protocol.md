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

# Frozen Event-Risk Protocol

```{raw} html
<p class="castalia-kicker">INQUIRY 001 · PREREGISTRATION · DEVELOPMENT ONLY</p>
```

This page records the fixed development evaluation for the first biotech event-risk model. The machine-readable source is [`config/biopharma_event_risk_protocol.json`](../../config/biopharma_event_risk_protocol.json), protocol `castalia-biopharma-event-risk-001`, version 1. The evaluator checks that its fixed feature allowlist matches the implementation and writes the protocol hash, target role, realized features, and any permitted deviations into every run summary.

## Question and estimand

Among independently sourced issuer disclosures of clinical-trial events, estimate the probability that the issuer's adjusted close-to-close return from the last pre-event close through the second close on or after the event date is at most −10%. This is event-conditioned downside risk. It does not estimate clinical efficacy, regulatory approval, a causal biology-to-return effect, or tradable alpha.

The current disclosure list is a manually selected source-lineage fixture. It is not a representative cohort and does not meet the sample gates. The protocol must not be relaxed to force a fit.

## Data and timing rules

- Event time comes from independently verified issuer, sponsor, or institutional disclosures. Registry completion dates are not substituted for public disclosure time.
- A date-only event maps to the first exchange session on or after its source date. Keep its precision label and interpret it at date-level only; do not infer intraday ordering.
- Features are cut at the prior US regular-session close (16:00 America/New_York), strictly before the event window. The event schedule, event-window market data, later publications, and unarchived current registry fields are prohibited predictors.
- Require adjusted close bars from a licensed provider and a matching SHA-256 manifest. Cover every event issuer, explicitly related issuer, SPY, and XBI.
- Estimate the market model from issuer returns over sessions −230 through −31, with at least 120 complete observations. The predeclared outcome sensitivity is a two-session additive SPY/XBI market-model CAR at or below −10%; it uses the same feature and fold policy.
- Keep one issuer-event row per market-relevant disclosure. Link related trial IDs without duplicating the return label. Purge any training outcome whose second matched session reaches or overlaps a test block.

## Predictors and model

Use only the fixed allowlist in the JSON protocol plus sorted, curated numeric `research_numeric_*_median` columns. Record the realized columns and panel checksum. Require at least two features and reject text or outcome columns. Median imputation with missingness indicators and standard scaling are fit separately inside each training fold. The fixed model is L2 logistic regression (`C=1.0`, `max_iter=2000`, `random_state=0`).

## Chronological evaluation

Cluster distinct event dates so a date cannot cross a split. Reserve the latest 20% of dates as a sealed final holdout. Development uses the first 80%: the initial training window is the first 40% of development dates, followed by three expanding chronological test blocks. Each scored fold requires at least 30 training events, 8 test events, and both target classes in training. If no fold qualifies, exit without fitting and do not lower thresholds. The current development command does not score or export holdout labels.

## Baselines and scorecard

Primary score is Brier score; confirmatory score is log loss; ROC AUC appears only when the test fold has both classes. Compare with (1) training-fold base rate, (2) training-only pre-event-volatility tertiles shrunk to the fold base rate with prior strength 5, and (3) training-only archived-trial-phase groups shrunk the same way. Show each fold, calibration from five fixed-width bins using development out-of-sample predictions, and issuer/calendar-quarter cluster counts.

Use a paired issuer × calendar-quarter pigeonhole bootstrap (1,000 repetitions, seed 2026) for baseline-minus-model score improvement. Withhold intervals unless there are at least 10 issuer and 10 quarter clusters and sparse crossings allow at least 80% of requested replicates. Never claim a signal from a pooled score alone or from an interval withheld for sparse clusters.

The event-risk scorecard is separate from a trading scorecard. Any future trading study must independently freeze its final evaluation and report net CAGR, benchmark-relative compounded wealth, maximum drawdown, volatility, Sharpe, Sortino, expected shortfall, turnover, exposure, risk-limit breaches, and 1×/2×/4× transaction-cost stress against cash, buy-and-hold, trend-following, and pre-catalyst-exit baselines.

## Reproduction

After licensed prices and a qualifying point-in-time event panel exist:

```bash
python scripts/build_biopharma_event_panel.py
python scripts/evaluate_event_risk.py
python scripts/evaluate_event_risk.py --target down_10pct_market_model_car_0_1
```

The second run is the predeclared sensitivity. Any changed threshold, fold count, holdout fraction, or non-protocol target requires `--allow-protocol-deviation`; the run records the difference. Preserve protocol versions rather than editing a version after seeing results. Reproduction status and source gates are summarized in the [biopharma source audit](../_static/biopharma-source-audit.json) and [RL replay readiness audit](../_static/rl-replay-readiness.json).
