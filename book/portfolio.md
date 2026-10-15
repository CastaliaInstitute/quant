# Biotech & Pharma Quant Research Portfolio

```{raw} html
<p class="castalia-kicker">CASTALIA INSTITUTE · WORK IN PROGRESS</p>
```

This site is a public portfolio for building toward quantitative research and research-engineering work at the intersection of biotech/pharma and markets. It is designed to make the work inspectable: a reader should be able to see the question, source records, timestamp policy, market data, assumptions, code, validation path, and limitations—not just a return chart.

The intended contribution is an interdisciplinary research practice grounded in my PhD background in computational biology, with electrical engineering, C++ systems work, and AI architecture also informing it. The biological background is useful for interpreting trial phase, endpoints, comparators, populations, and publication context; market timing, point-in-time joins, statistical validation, and empirical finance evidence still have to be earned in the work shown here.

## Evidence I am building

| Capability | Portfolio artifact | Status |
| --- | --- | --- |
| Return measurement | Net return, volatility, Sharpe, Sortino, maximum drawdown, Calmar, benchmark-relative metrics, and turnover | Implemented in the Python research package |
| Reproducible simulation | Seeded biotech catalyst generator and a long-or-cash Gymnasium environment that separates program advancement from market reaction | Implemented; Phase II/III advancement priors use published aggregate rates; price process remains synthetic |
| RL experimentation | Tabular Q-learning compared on matched paths with cash, buy-and-hold, trend, and pre-catalyst exit rules; reports return and drawdown alongside transition/price-response diagnostics | Executable simulator study; Q policy has 0% median catalyst exposure and −2.28% median net CAGR in this synthetic world; no market generalization claim |
| Historical source acquisition | ClinicalTrials.gov cohort, linked Europe PMC article metadata, issuer-sourced public readout timestamps, and a pinned open clinical-outcome benchmark | Ten trial-to-issuer mappings and nine disclosures span four therapeutic areas; the 11,012-row CTO audit exposes a forbidden current-status rule with 97.05% apparent accuracy and verifies no as-of predictors |
| Historical price/event study | Join trial and research context to licensed OHLCV and quantify market-model event-window risk | Two-factor OLS event-study outputs are implemented; licensed bars and a wider verified cohort are still needed, so no market result is published |
| AI impact monitoring | Track AI's role at the molecule, trial, and company levels; measure advancement, trial operations, and issuer-market response separately | Versioned registry discovery feed, separate exposure/outcome ledgers, and coverage audit are implemented; one curated rentosertib Phase IIa case is insufficient for AI-versus-conventional inference, and issuer-market impact still needs licensed prices |
| Research communication | Jupyter Book with source lineage, metric definitions, event-time semantics, and adversarial review | Source maintained in this repository |

## What a quant reviewer should be able to inspect

The portfolio is organized around evidence for the work, not a claim of readiness based on credentials alone.

| Hiring signal | Evidence to inspect | Current proof and remaining gap |
| --- | --- | --- |
| Statistical judgment | Falsifiable question, leakage controls, chronological folds, baselines, uncertainty, and failed runs | Protocol and simulator work are present; the historical event model still needs a broader cohort and licensed prices |
| Financial measurement | Net compounded returns, benchmark-relative results, drawdown, turnover, and cost sensitivity | Metrics are implemented; no empirical result is published yet |
| ML and RL research | Reproducible experiments, matched-seed policy comparisons, and an honest transition from synthetic to historical replay | Synthetic RL study is reproducible but uncalibrated; no market generalization claim |
| Data engineering | Versioned trial records, source hashes, timestamps, security mapping, and price-vendor lineage | Registry/article ingestion, pinned external-cohort audit, and panel builder exist; archived point-in-time versions and licensed market prices remain gaps |
| Research engineering | Forkable components, bounded execution, deterministic configuration, and usable documentation | Core package, book, and cell Worker are in the repository; public deployment and broader runtime review remain pending |
| Biopharma domain work | Correct interpretation of phases, endpoints, publication timing, and clinical outcomes | PhD background informs the question; empirical feature construction and multi-area replication remain to be demonstrated |

## Metric choices

For a prediction claim, evaluate downside probabilities with Brier score and log loss against a chronological training-window base rate; use ROC AUC only as a secondary ranking measure when both classes occur. For a strategy or RL policy, lead with net compounded return and benchmark-relative compounded return together with maximum drawdown. Publish volatility, Sharpe/Sortino, tail loss, turnover, and cost stress beside them. The RL reward is log net wealth, while decisions are judged across matched seeds and lower-tail outcomes. The [evidence review](research/evidence-review.md) records how published clinical-transition and market-response studies inform the simulator without conflating their targets.

## How the work will be judged

The first standard is **correctness of the experiment**, not a target Sharpe or return. A portfolio-quality study needs timestamp discipline, costs, benchmark context, chronological evaluation, a record of variants tried, and clear communication of uncertainty. The selected scorecard is documented in [Return Metrics](research/metrics.md).

RL experiments begin in a controlled synthetic gym, where the transition rules and reward can be inspected. A learned policy must be evaluated on held-out episodes and multiple seeds against simple policies. Synthetic performance validates only behavior in that simulator. A later historical study must separate training, validation, and a final untouched period; it must not let repeated policy search consume the holdout.

## Current research status

**Five evidence lanes.** The RL simulator uses published aggregate Phase II/III program-advancement rates but still uses synthetic issuer returns. The ClinicalTrials.gov/Europe PMC/SEC ingest and event panel support point-in-time catalyst analysis; its nine manually sourced disclosures span COVID-19 vaccines, Alzheimer’s disease, asthma, and oncology, but remain a small fixture with several date-only timestamps. A pinned external CTO benchmark adds a distinct clinical-outcome label audit; its filtered human-label subset is not a representative transition prior and lacks verified first-public-disclosure timestamps and usable stock-return histories. The [AI Impact Watch](research/ai-impact.md) now pairs a registry discovery feed with a curated rentosertib Phase IIa case and separate exposure/outcome ledgers; one candidate cannot estimate AI's causal effect or a general advancement rate. No licensed price bars have been joined, so market-response and AI-related issuer-return estimates remain unavailable. See the <a href="_static/biopharma-source-audit.json">source audit</a>, <a href="_static/ai-impact-monitor.json">AI impact coverage audit</a>, <a href="_static/cto-human-labels-audit.json">CTO audit</a>, [evidence review](research/evidence-review.md), [RL study](research/rl-study.md), and [data-source guide](data-sources.md).

There is no validated historical model, brokerage integration, or claim of a repeatable market edge in this portfolio yet. The price vendor, licensed price file, delisted-issuer coverage, and point-in-time trial snapshots remain required before the event panel can support out-of-sample analysis. The live-cell Worker runs only bounded teaching examples. RL training runs in the Python package, not in that Worker.

## A path toward stronger evidence

1. Expand the seed events beyond the correlated COVID-vaccine readouts, covering therapeutic areas, phases, positive/negative/ambiguous outcomes, partnerships, and failed or delisted issuers.
2. Add event-source verification and archived point-in-time trial versions, then freeze source timestamps and ticker/issuer mappings.
3. Import an appropriate licensed daily and intraday market-data history, including sector and broad-market comparators.
4. Establish raw-return, market-model CAR, event-downside, and calibration baselines; keep the final chronological period untouched.
5. Use clinical-outcome labels only in a separately defined progression/approval benchmark; do not transfer the selected CTO label fraction into the simulator.
6. Calibrate empirical replay and RL reward distributions from training-window market outcomes only; preserve event-level and issuer-level dependence in the gym.
7. Train RL only within training windows; tune on validation windows; preserve the final period untouched.
8. Publish permissible source identifiers, code revision, configuration, cohort selection, data checksums, event windows, objections, and failed runs.

This roadmap is the intended portfolio standard, not a claim that each stage is complete.
