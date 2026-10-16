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
| RL experimentation | Tabular Q-learning compared on matched paths with cash, buy-and-hold, trend, and pre-catalyst exit rules; reports return and drawdown alongside transition/price-response diagnostics | Ten-training-seed replication: Q-minus-trend relative-wealth interval −6.9 to +12.0 pp spans zero; reward audit explains cash preference from negative synthetic expected log growth; no market generalization claim |
| Historical source acquisition | ClinicalTrials.gov cohort, linked Europe PMC article metadata, issuer-sourced public readout timestamps, and a pinned open clinical-outcome benchmark | 27 trial-to-issuer mappings and 26 disclosures span eight therapeutic areas/indications; the 11,012-row CTO audit exposes a forbidden current-status rule with 97.05% apparent accuracy and verifies no as-of predictors |
| Historical price/event study | Join trial and research context to licensed OHLCV and quantify market-model event-window risk | Two-factor OLS event-study outputs are implemented; licensed bars and a wider verified cohort are still needed, so no market result is published |
| AI impact monitoring | Track AI's role at the molecule, trial, company, patient, workforce, and environmental levels; measure scientific, operational, economic, access, safety, labor, and footprint effects separately | Versioned registry discovery feed, separate exposure/outcome ledgers, and six-lane coverage audit are implemented; one curated candidate plus published 2024/2026 cohort studies provide context but no matched AI-versus-conventional estimate, and issuer-market impact still needs licensed prices |
| Research communication | Jupyter Book with source lineage, metric definitions, event-time semantics, and adversarial review | Source maintained in this repository |

## What a quant reviewer should be able to inspect

The portfolio is organized around evidence for the work, not a claim of readiness based on credentials alone.

| Hiring signal | Evidence to inspect | Current proof and remaining gap |
| --- | --- | --- |
| Statistical judgment | Falsifiable question, leakage controls, chronological folds, baselines, uncertainty, and failed runs | Protocol and simulator work are present; the historical event model still needs a broader cohort and licensed prices |
| Financial measurement | Net compounded returns, benchmark-relative results, drawdown, turnover, and cost sensitivity | Metrics are implemented; no empirical result is published yet |
| Portfolio construction and risk | Multi-asset weights, issuer/sector limits, risk budgets, turnover, and capacity-aware costs | A deterministic synthetic comparison now runs cash, equal-weight, inverse-volatility, and trend portfolios through the lagged backtest with issuer/sector caps and cost stress. This demonstrates the portfolio construction path only; covariance-aware risk budgets, realistic fills, and empirical portfolio evaluation remain future work |
| ML and RL research | Reproducible experiments, matched-seed policy comparisons with uncertainty, and an honest transition from synthetic to historical replay | Crossed-seed bootstrap includes training and evaluation seed variation under one synthetic generator; return intervals span zero, the Q policy mostly chooses cash, and the 10-policy sample is exploratory |
| Data engineering | Versioned trial records, source hashes, timestamps, security mapping, and price-vendor lineage | Registry/article ingestion, pinned external-cohort audit, and panel builder exist; archived point-in-time versions and licensed market prices remain gaps |
| Research engineering | Forkable components, bounded execution, deterministic configuration, and usable documentation | Core package, book, and cell Worker are in the repository; public deployment and broader runtime review remain pending |
| Biopharma domain work | Correct interpretation of phases, endpoints, publication timing, and clinical outcomes | PhD background informs the question; empirical feature construction and multi-area replication remain to be demonstrated |

## Metric choices

For a prediction claim, evaluate downside probabilities with Brier score and log loss against a chronological training-window base rate; use ROC AUC only as a secondary ranking measure when both classes occur. For an RL policy, select the strongest non-RL baseline on separate validation paths, then compare paired net benchmark-relative compounded wealth on untouched final paths. Report net CAGR, maximum drawdown, volatility, Sharpe/Sortino, tail loss, turnover, exposure, and cost stress alongside it. The RL reward is log net wealth with `γ=1`; that is the training objective, while policy claims depend on paired final evaluation and predeclared risk limits. Evidence labels distinguish simulator mechanics from historical replay and frozen out-of-sample results. The [evidence review](research/evidence-review.md) records how published clinical-transition and market-response studies inform the simulator without conflating their targets.

This scorecard covers the research pipeline expected in current quantitative-research roles, including data processing, feature design, model training, portfolio construction, backtesting, and performance analysis ([Point72 quantitative researcher role](https://careers.point72.com/CSJobDetail?jobCode=CSS-0012688&jobName=quantitative-researcher&locale=English&location=Hong+Kong&retURL=%2FCSCareerSearch)). The [multi-asset simulation](research/portfolio-simulation.md) demonstrates portfolio construction with issuer/sector caps, lagged execution, and transaction-cost stress. It is still synthetic. Historical portfolio evidence requires approved prices, delisted-issuer coverage, and a frozen chronological evaluation. Keep probability calibration as the model-selection criterion; judge any resulting allocation separately by net portfolio returns and risk.

## How the work will be judged

The first standard is **correctness of the experiment**, not a target Sharpe or return. A portfolio-quality study needs timestamp discipline, costs, benchmark context, chronological evaluation, a record of variants tried, and clear communication of uncertainty. The selected scorecard is documented in [Return Metrics](research/metrics.md).

RL experiments begin in a controlled synthetic gym, where the transition rules and reward can be inspected. A learned policy must be evaluated on held-out episodes and multiple seeds against simple policies. Synthetic performance validates only behavior in that simulator. The next qualifying portfolio study must be multi-asset and compare RL with cash, buy-and-hold, equal-weight, inverse-volatility, trend, and pre-catalyst exit under identical issuer/sector constraints and execution costs. A historical study must separate training, validation, and a final untouched period; it must not let repeated policy search consume the holdout. The {ref}`RL ladder and evidence gates <hiring-portfolio-rl-ladder>` specify what is required before results count as historical or out-of-sample evidence.

## Current research status

**Five evidence lanes.** The RL simulator uses published aggregate Phase II/III program-advancement rates but still uses synthetic issuer returns. The ClinicalTrials.gov/Europe PMC/SEC ingest and event panel support point-in-time catalyst analysis; its 26 manually sourced disclosures span vaccines, Alzheimer’s disease, asthma, oncology, eosinophilic esophagitis, heart failure, chronic rhinosinusitis with nasal polyps, and Duchenne muscular dystrophy. The expanded cohort remains small and has date-only timestamps. A pinned external CTO benchmark adds a distinct clinical-outcome label audit; its filtered human-label subset is not a representative transition prior and lacks verified first-public-disclosure timestamps and usable stock-return histories. The [AI Impact Watch](research/ai-impact.md) pairs a registry discovery feed and curated rentosertinib case with newer published pipeline-cohort evidence; none provides a matched AI-versus-conventional estimate. No licensed price bars have been joined, so market-response and AI-related issuer-return estimates remain unavailable. See the <a href="_static/biopharma-source-audit.json">source audit</a>, <a href="_static/ai-impact-monitor.json">AI impact coverage audit</a>, <a href="_static/cto-human-labels-audit.json">CTO audit</a>, [evidence review](research/evidence-review.md), [RL study](research/rl-study.md), and [data-source guide](data-sources.md).

There is no validated historical model, brokerage integration, or claim of a repeatable market edge in this portfolio yet. The price vendor, licensed price file, delisted-issuer coverage, and point-in-time trial snapshots remain required before the event panel can support out-of-sample analysis. The live-cell Worker runs only bounded teaching examples. RL training runs in the Python package, not in that Worker.

## A path toward stronger evidence

1. Expand the seed events beyond the correlated COVID-vaccine readouts, covering therapeutic areas, phases, positive/negative/ambiguous outcomes, partnerships, and failed or delisted issuers.
2. Add event-source verification and archived point-in-time trial versions, then freeze source timestamps and ticker/issuer mappings.
3. Import an appropriate licensed daily and intraday market-data history, including sector and broad-market comparators.
4. Establish raw-return, market-model CAR, event-downside, and calibration baselines; keep the final chronological period untouched.
5. Build a multi-asset portfolio layer with equal-weight and inverse-volatility baselines, issuer/sector caps, a cash option, and cost-aware rebalancing; publish exposure, turnover, drawdown, and benchmark-relative returns.
6. Use clinical-outcome labels only in a separately defined progression/approval benchmark; do not transfer the selected CTO label fraction into the simulator.
7. Calibrate empirical replay and RL reward distributions from training-window market outcomes only; preserve event-level and issuer-level dependence in the gym.
8. Extend RL from the one-issuer mechanics gym only after transparent multi-asset rules are established. Train inside chronological training windows, tune on validation windows, enforce the same portfolio/risk constraints, and preserve the final period untouched.
9. Publish permissible source identifiers, code revision, configuration, cohort selection, data checksums, event windows, objections, and failed runs.

This roadmap is the intended portfolio standard, not a claim that each stage is complete.
