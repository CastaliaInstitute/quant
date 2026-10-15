# Quant.

**A quantitative research portfolio built around a forkable system.** Quant. gives researchers a reproducible core they can tune into their own quant applications. Its first domain is biotech and pharma: clinical-trial readouts, biomedical research, regulatory catalysts, issuer-specific gap risk, and the challenge of joining those events to point-in-time financial data.

Castalia Institute's **MagAI (Quant)** program will use this system as its shared research environment. The open-source platform remains useful on its own; learners can study its conventions, modify a fork, and build a research application around a question of their choosing.

Live trading is intentionally out of scope until a strategy has passed documented validation and risk review.

> The RL gym and ML example use illustrative synthetic data. They are not investment advice and do not represent historical trading performance.

## The forkable system

Quant. is intended to be a small, inspectable foundation rather than a fixed trading strategy or a hosted black box. Fork the repository, preserve the research ledger, and adapt the replaceable parts to a new instrument universe, data source, hypothesis, or workflow.

| System seam | What a fork can tune |
| --- | --- |
| Research question | Hypothesis, target, horizon, falsification criteria |
| Data | Provider, instrument universe, calendar, adjustment and missing-data policy |
| Features and models | Feature definitions, estimator, parameters, training schedule |
| Simulation | Signal timing, fill assumptions, fees, spread, slippage |
| Risk | Long-or-cash constraints, exposure caps, drawdown rules |
| Evidence | Chronological splits, baselines, sensitivity tests, review and publication |

The starter keeps these choices visible in code and experiment records. A user fork can replace a component without changing the core expectation: every result should be reconstructable from its declared inputs and assumptions.

## What is here

- A Castalian Jupyter Book in `book/` that serves as the public research and career portfolio, including current artifacts, limitations, metric choices, and next evidence gates.
- A fork guide and simulation/RL gym research guide that define the extension points and validation discipline for simulator-based research and the planned MagAI (Quant) program.
- Page-local Python cells that run on the Cloudflare Python Worker in `worker/`. The Worker is stateless: the browser sends the page's cells in order to reconstruct variables for each run.
- A small Python research package with one-period signal lag, proportional transaction costs, net return metrics, benchmark alignment, 1×/2×/4× cost sensitivity, and equal-weight / inverse-volatility portfolio allocation and rebalancing baselines with issuer and sector caps.
- A seeded Gymnasium-compatible synthetic biotech catalyst environment, with separately sampled Phase II/III program advancement and market reactions. Advancement priors use published 2011–2020 aggregate transition rates; market reactions remain synthetic. Tabular Q-learning is compared with cash, buy-and-hold, a trend rule, and a pre-catalyst risk rule.
- A historical event-data pipeline for ClinicalTrials.gov, biomedical publication metadata, SEC issuer filings, and a user-supplied licensed stock-price file, with SPY and XBI context; point-in-time features exclude records unavailable at the decision cutoff, and source hashes are recorded in a local panel manifest. It estimates a pre-event two-factor market model and keeps abnormal-return outputs separate from pre-event model features. Fetched and processed datasets remain local and are excluded from Git.
- A pinned audit of the MIT-licensed Clinical Trial Outcome human-label benchmark. Its [leakage review](book/research/cto-audit.md) quantifies a forbidden 97.05%-accurate current-status rule and explains why zero current registry fields are yet verified as point-in-time predictors; no labels feed the RL priors or market-return model.
- An AI-impact monitoring lane for candidate-level discovery, clinical-trial operations, and company/market effects. A versioned ClinicalTrials.gov keyword snapshot feeds a manually curated, point-in-time evidence ledger; keyword hits are not treated as AI-discovered drugs or outcome evidence. The watch tracks recent clinical-pipeline cohort publications separately from candidate-level evidence and does not interpret those descriptive cohorts as causal AI effects.
- A gated expanding-window event-risk evaluator that compares overall, volatility-conditioned, and trial-phase-conditioned historical rates with a regularized logistic model, reports probability scores, and keeps a final chronological block untouched.
- A synthetic ML signal demonstration that uses chronological train/test separation.
- Cloudflare Pages and Worker deployment configuration for `quant.castalia.institute` and `cells.quant.castalia.institute`.

## Quick start

Requires Python 3.10+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev,rl]' -r requirements-book.txt
PYTHONPATH=worker/src pytest
python -m quantlab.demo
python scripts/run_rl_study.py
python scripts/run_rl_stress.py
python scripts/run_rl_training_robustness.py
python scripts/audit_rl_reward_incentives.py
python scripts/ingest_biopharma.py --with-sec-filings
python scripts/monitor_ai_trials.py
python scripts/audit_ai_impact.py
python scripts/audit_cto_outcomes.py
jupyter-book build book --path-output book
```

Historical registry, biomedical-publication, and issuer filing metadata have been pulled for ten trial-to-issuer mappings and nine sourced disclosures across four therapeutic areas. The cohort is a source-lineage fixture, not a training sample. Market prices are fetched separately through a provider account or imported from a licensed CSV; see [the biopharma data guide](book/data-sources.md). No stock-price file has been provided yet, so there is no historical event-return result or fitted historical model.

After a broader event cohort, archived point-in-time trial versions, and licensed price bars are available, build the local panel and run the gated walk-forward evaluator:

```bash
python scripts/build_biopharma_event_panel.py
python scripts/evaluate_event_risk.py
# Compare the same walk-forward gates on factor-adjusted downside:
python scripts/evaluate_event_risk.py --target down_10pct_market_model_car_0_1
```

The evaluator requires enough distinct historical event dates and at least 30 training / 8 test events per fold by default. It deliberately exits on the current nine-disclosure fixture instead of fitting an unstable model.

The CTO benchmark audit downloads a pinned 2020–2024 human-labeled subset (about 10 MB) into ignored `data/raw/cto/` and writes aggregate provenance/coverage to `reports/cto-human-labels-audit.json`. It is a separate clinical-outcome benchmark, not the market-event model: its subset was selected to remove easy cases, and its current-record fields are not point-in-time features.

## Return scorecard

For eventual trading evaluation, primary metrics are net CAGR, annualized volatility, Sharpe ratio, maximum drawdown, annualized turnover, and sensitivity to 1×/2×/4× transaction costs. For the initial biotech event-risk question, report calibration and tail-risk metrics: 5% historical VaR/expected shortfall, worst event move, event counts, and phase/issuer distributions. Include biotech-index and broad-market context on matched dates. Definitions and limits are set out in [book/research/metrics.md](book/research/metrics.md).

The portfolio construction baselines are weight generators, not backtests. They cap exposures by retaining the excess as cash rather than silently spreading it across other names:

```python
import pandas as pd
from quantlab import allocate_portfolio

volatility = pd.Series({
    "ISSUER_A": 0.60, "ISSUER_B": 0.45, "ISSUER_C": 0.30, "ISSUER_D": 0.20,
})
sectors = pd.Series({
    "ISSUER_A": "Oncology", "ISSUER_B": "Oncology",
    "ISSUER_C": "Immunology", "ISSUER_D": "Immunology",
})
allocation = allocate_portfolio(
    list(volatility.index),
    method="inverse_volatility",
    annualized_volatility=volatility,
    max_asset_weight=0.40,
    sectors=sectors,
    max_sector_weight=0.60,
)
print(allocation.weights)
print("Cash weight:", allocation.cash_weight)
```

Volatility estimates must be computed from information available at each decision date. `portfolio_backtest` consumes time-aligned asset-return and target-weight panels, executes each close-time target on the next row, charges costs on absolute weight turnover, and treats uninvested cash as zero-return unless a cash series is supplied. `portfolio_cost_sensitivity` evaluates one fixed target-weight path at 1×/2×/4× transaction costs. These functions do not fit forecasts, estimate covariance, or model fills; no empirical portfolio result is claimed.

## Research principles

Every published experiment should record its hypothesis, exact data source and version, universe, train/validation/test periods, features, model parameters, execution timing, transaction costs, and out-of-sample results. Signals are lagged before execution. Do not tune against the final holdout period. Compare all strategies against buy-and-hold and a simple trend baseline.

## Initial research question

In a point-in-time biotech/pharma universe, do observable trial, research-publication, and market features help characterize stock-price risk around clinical results disclosures? The initial study will estimate event-window downside risk, not try to predict trial success or claim directional alpha. ClinicalTrials.gov `ResultsFirstPostDate` and linked PubMed publication dates are observable proxies, not necessarily the first moment results reached investors; company press releases and intraday timing must be added where verified. The issuer-to-ticker mapping and licensed price vendor must be explicitly versioned before the analysis.

The first runnable RL artifact remains a synthetic catalyst gym, so its transition rules can be inspected before fitting policies to sparse, noisy historical catalysts. It is not empirically calibrated. Historical source acquisition and event-panel construction are separate commands; the output is local because market-data redistribution rights depend on the selected provider. RL training runs locally, not on the bounded public Worker.

## Safety and limitations

- Synthetic data is for software demonstrations only.
- This project does not currently connect to a brokerage or execute orders.
- Paper trading should be added only after historical evaluation, leakage checks, and risk controls are independently reviewed.
- Live trading is disabled by design.

## Website

The published research book is generated at `book/_build/html/`. To preview it, run `python -m http.server 8000 --directory book/_build/html` from this directory and open `http://localhost:8000`.

## Live research cells

Cells run through a Cloudflare Python Worker configured in `worker/wrangler.toml`. The public runtime accepts a small Python subset with capped source length, cell count, loop ranges, arithmetic growth, and output. It rejects imports, attribute access, arbitrary functions, filesystem and network access, and brokerage operations. Each request reconstructs the visible cells in memory and discards that state after returning outputs. It stores no cell code or user session.

The GitHub Actions deployment requires `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID`. Create a custom token with the account, zone, and user permissions listed in the [Cloudflare deployment runbook](book/deployment.md), then store it as a repository Actions secret; do not put it in the repository. The workflow creates the `quantlab` Pages project if needed, deploys the Worker and book, associates `quant.castalia.institute` with Pages, and points its proxied CNAME at `quantlab.pages.dev`. The Worker custom domain is declared in `worker/wrangler.toml`. DNS changes run only after the Pages deployment succeeds.

## Build around a fork

1. Fork this repository and write a question with a clear way it could be disproved.
2. Declare your universe and data source, including licensing, timestamps, adjustments, and a version or checksum.
3. Change the features, model, or strategy in your fork; leave the signal-to-execution timing explicit.
4. Set realistic costs and risk limits, then compare against simple baselines on chronological windows.
5. Publish the experiment record and preserve failed runs as well as successful ones.

The public book's Worker runs a deliberately small Python teaching subset. For a serious fork, run the full research stack in a controlled local or private environment, then publish the reproducible artifacts and reviewable code. Do not put credentials, proprietary datasets, or brokerage bindings in the public cell Worker.

## License

MIT. See [LICENSE](LICENSE).
