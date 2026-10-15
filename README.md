# QuantLab AI

An open-source quantitative research platform for reproducible signal research, rigorous backtesting, and paper trading. Live trading is intentionally out of scope until a strategy has passed documented validation.

> The included web dashboard and ML example use illustrative synthetic data. They are not investment advice and do not represent real trading performance.

## What is here

- A responsive research dashboard at `site/` for the project website.
- A small Python backtesting engine with one-period signal lag, proportional transaction costs, and common risk metrics.
- A synthetic ML signal demonstration that uses chronological train/test separation.
- GitHub Pages deployment configuration for `quant.castalia.institute`.

## Quick start

Requires Python 3.10+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest
python -m quantlab.demo
```

## Research principles

Every published experiment should record its hypothesis, exact data source and version, universe, train/validation/test periods, features, model parameters, execution timing, transaction costs, and out-of-sample results. Signals are lagged before execution. Do not tune against the final holdout period. Compare all strategies against buy-and-hold and a simple trend baseline.

## Initial hypothesis

Can short-term momentum, volatility, and volume predict next-day risk-adjusted returns in liquid US-listed ETFs? Initial universe: SPY, QQQ, IWM, and TLT. Start with long-or-cash positions, no leverage, options, or shorting.

## Safety and limitations

- Synthetic data is for software demonstrations only.
- This project does not currently connect to a brokerage or execute orders.
- Paper trading should be added only after historical evaluation, leakage checks, and risk controls are independently reviewed.
- Live trading is disabled by design.

## Website

The standalone website lives in `site/`. To preview it locally, run `python -m http.server 8000 --directory site` from this directory and open `http://localhost:8000`.

## License

MIT. See [LICENSE](LICENSE).
