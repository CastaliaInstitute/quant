#!/usr/bin/env python3
"""Build a deterministic, explicitly synthetic multi-asset portfolio example."""
from __future__ import annotations

import json
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np
import pandas as pd

from quantlab import allocate_portfolio, portfolio_cost_sensitivity


OUTPUT = ROOT / "book/_static/synthetic-portfolio-demo.json"
ASSETS = ("BIO_A", "BIO_B", "PHARMA_A", "PHARMA_B")
SECTORS = pd.Series({"BIO_A": "biotech", "BIO_B": "biotech", "PHARMA_A": "pharma", "PHARMA_B": "pharma"})


def generate_market(seed: int = 2718, periods: int = 1_500) -> tuple[pd.DataFrame, pd.Series, dict[str, list[int]]]:
    """Make a correlated toy market with independent scheduled issuer catalysts."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2018-01-02", periods=periods, name="date")
    market = rng.normal(0.00025, 0.009, periods)
    biotech_factor = 0.35 * market + rng.normal(0.0001, 0.014, periods)
    pharma_factor = 0.65 * market + rng.normal(0.0001, 0.008, periods)
    returns: dict[str, np.ndarray] = {}
    events: dict[str, list[int]] = {}
    for i, asset in enumerate(ASSETS):
        factor = biotech_factor if asset.startswith("BIO") else pharma_factor
        beta = 0.55 if asset.startswith("BIO") else 0.75
        path = beta * factor + rng.normal(0.0001, 0.018 if asset.startswith("BIO") else 0.011, periods)
        event_indices = list(range(80 + i * 7, periods, 126))
        for index in event_indices:
            # Catalyst market gaps are illustrative draws; no clinical result label is modeled here.
            positive_gap = rng.random() < 0.46
            gap = (0.12 if asset.startswith("BIO") else 0.07) if positive_gap else (-0.17 if asset.startswith("BIO") else -0.09)
            path[index] += gap
        returns[asset] = path
        events[asset] = event_indices
    return pd.DataFrame(returns, index=dates), pd.Series(market, index=dates, name="SPY"), events


def strategy_weights(asset_returns: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Create close-time target panels; the backtester applies them next period."""
    weights: dict[str, pd.DataFrame] = {}
    empty = pd.DataFrame(0.0, index=asset_returns.index, columns=ASSETS)
    weights["cash"] = empty.copy()

    equal = pd.DataFrame(0.0, index=asset_returns.index, columns=ASSETS)
    inverse = equal.copy()
    trend = equal.copy()
    for i in range(len(asset_returns)):
        available_history = asset_returns.iloc[: i + 1]
        names = list(ASSETS)
        allocation = allocate_portfolio(
            names,
            method="equal_weight",
            max_asset_weight=0.35,
            sectors=SECTORS,
            max_sector_weight=0.55,
        )
        equal.iloc[i] = allocation.weights.to_numpy()
        if len(available_history) >= 20:
            volatility = available_history.tail(20).std(ddof=1) * np.sqrt(252)
            allocation = allocate_portfolio(
                names,
                method="inverse_volatility",
                annualized_volatility=volatility,
                max_asset_weight=0.35,
                sectors=SECTORS,
                max_sector_weight=0.55,
            )
            inverse.iloc[i] = allocation.weights.to_numpy()
        if len(available_history) >= 20:
            momentum = (1.0 + available_history.tail(20)).prod() - 1.0
            selected = momentum[momentum > 0].index.tolist()
            if selected:
                allocation = allocate_portfolio(
                    selected,
                    method="equal_weight",
                    max_asset_weight=0.35,
                    sectors=SECTORS,
                    max_sector_weight=0.55,
                )
                trend.loc[asset_returns.index[i], allocation.weights.index] = allocation.weights
    weights["equal_weight"] = equal
    weights["inverse_volatility"] = inverse
    weights["20d_trend"] = trend
    return weights


def main() -> None:
    asset_returns, spy_returns, event_indices = generate_market()
    rng = np.random.default_rng(31415)
    xbi_returns = 0.72 * spy_returns.to_numpy() + rng.normal(0.00015, 0.013, len(spy_returns))
    benchmark = pd.Series(xbi_returns, index=spy_returns.index, name="XBI")
    weights = strategy_weights(asset_returns)
    # The XBI-like comparator is the matched benchmark path, not an issuer
    # portfolio policy.
    policies = weights
    report = {
        "evidence_status": "synthetic_portfolio_mechanics_only",
        "interpretation": "Deterministic simulator output; not historical market performance, a fitted model, or evidence of alpha.",
        "code_sha256": {
            "generator": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "portfolio_library": hashlib.sha256((ROOT / "src/quantlab/portfolio.py").read_bytes()).hexdigest(),
            "return_metrics": hashlib.sha256((ROOT / "src/quantlab/backtest.py").read_bytes()).hexdigest(),
        },
        "market": {
            "seed": 2718,
            "periods": len(asset_returns),
            "first_date": asset_returns.index[0].date().isoformat(),
            "last_date": asset_returns.index[-1].date().isoformat(),
            "assets": list(ASSETS),
            "sectors": SECTORS.to_dict(),
            "scheduled_catalyst_counts": {key: len(value) for key, value in event_indices.items()},
            "return_generator": "correlated Gaussian market/sector factors plus independently sampled illustrative issuer catalyst gaps",
            "xbi_benchmark_generator": "synthetic broad-market-linked sector series",
        },
        "protocol": {
            "decision_and_execution": "targets observed at close t are applied to return at t+1",
            "risk_constraints": {"max_asset_weight": 0.35, "max_sector_weight": 0.55, "long_only": True, "cash_allowed": True},
            "transaction_cost_bps_per_unit_turnover": 5.0,
            "cost_multipliers": [1.0, 2.0, 4.0],
            "baseline_selection": "No selection or tuning; all policies are fixed demonstrations.",
            "benchmark": "Synthetic XBI-like return path; not observed XBI prices.",
        },
        "policies": {},
    }
    for name, target_weights in policies.items():
        sensitivity = portfolio_cost_sensitivity(
            asset_returns,
            target_weights,
            benchmark_returns=benchmark,
            base_cost_bps=5.0,
            multipliers=(1.0, 2.0, 4.0),
        )
        report["policies"][name] = {
            "target_weight_summary": {
                "mean_exposure_at_decision": float(target_weights.sum(axis=1).mean()),
                "max_asset_weight": float(target_weights.max().max()),
                "max_sector_weight": float(target_weights.T.groupby(SECTORS).sum().T.max().max()),
            },
            "cost_sensitivity": sensitivity.to_dict(orient="records"),
        }
    OUTPUT.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Wrote synthetic multi-asset portfolio illustration: {OUTPUT}")
    print("Synthetic mechanics only; no historical or investment-performance claim.")


if __name__ == "__main__":
    main()
