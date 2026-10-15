"""Small, explicit long-or-cash daily backtest primitives."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd
from pandas import DataFrame


@dataclass(frozen=True)
class BacktestResult:
    returns: pd.Series
    positions: pd.Series
    equity: pd.Series
    turnover: pd.Series
    costs: pd.Series


def backtest(
    asset_returns: pd.Series,
    signals: pd.Series,
    transaction_cost_bps: float = 5.0,
) -> BacktestResult:
    """Run a daily long-or-cash strategy with signals executed next period.

    `signals` are observed at the close of a period and therefore shifted by one
    row before being applied to the following period's return. Position changes
    incur proportional costs; signals are clipped to [0, 1].
    """
    if transaction_cost_bps < 0:
        raise ValueError("transaction_cost_bps must be non-negative")
    aligned = pd.concat(
        [asset_returns.rename("asset_return"), signals.rename("signal")], axis=1
    ).dropna()
    if aligned.empty:
        empty = pd.Series(dtype=float)
        return BacktestResult(empty, empty, empty, empty, empty)

    positions = aligned["signal"].clip(0.0, 1.0).shift(1).fillna(0.0)
    turnover = positions.diff().abs()
    turnover.iloc[0] = positions.iloc[0]
    costs = turnover * (transaction_cost_bps / 10_000.0)
    strategy_returns = positions * aligned["asset_return"] - costs
    equity = (1.0 + strategy_returns).cumprod()
    return BacktestResult(
        strategy_returns.rename("strategy_return"),
        positions.rename("position"),
        equity.rename("equity"),
        turnover.rename("turnover"),
        costs.rename("cost"),
    )


def performance_metrics(
    returns: pd.Series,
    periods_per_year: int = 252,
    risk_free_rate: float = 0.0,
    benchmark_returns: pd.Series | None = None,
) -> dict[str, float]:
    """Summarize periodic net returns with an explicit annual risk-free rate.

    Sharpe is the conventional square-root annualized estimate; serial dependence
    can make that estimate misleading, so it should be read with the return path
    and validation protocol rather than as a stand-alone score.
    """
    if periods_per_year <= 0:
        raise ValueError("periods_per_year must be positive")
    if risk_free_rate <= -1:
        raise ValueError("risk_free_rate must be greater than -100%")

    values = returns.dropna().astype(float)
    aligned_benchmark = None
    if benchmark_returns is not None:
        aligned = pd.concat(
            [values.rename("strategy"), benchmark_returns.dropna().astype(float).rename("benchmark")],
            axis=1,
        ).dropna()
        values = aligned["strategy"]
        aligned_benchmark = aligned["benchmark"]
    if values.empty:
        empty = {
            "observation_count": 0,
            "total_return": 0.0,
            "annualized_return": 0.0,
            "annualized_volatility": 0.0,
            "sharpe": 0.0,
            "sortino": 0.0,
            "max_drawdown": 0.0,
            "calmar": 0.0,
            "value_at_risk_95": 0.0,
            "expected_shortfall_95": 0.0,
        }
        if benchmark_returns is not None:
            empty.update({
                "benchmark_total_return": 0.0,
                "benchmark_relative_compounded_return": 0.0,
                "excess_wealth_difference": 0.0,
                "information_ratio": 0.0,
            })
        return empty

    if (values <= -1.0).any() or (aligned_benchmark is not None and (aligned_benchmark <= -1.0).any()):
        raise ValueError("periodic returns must be greater than -100%")

    per_period_rf = (1.0 + risk_free_rate) ** (1.0 / periods_per_year) - 1.0
    excess = values - per_period_rf
    wealth = float((1.0 + values).prod())
    total_return = wealth - 1.0
    annualized_return = wealth ** (periods_per_year / len(values)) - 1.0 if wealth > 0 else -1.0
    volatility = float(values.std(ddof=1) * np.sqrt(periods_per_year)) if len(values) > 1 else 0.0
    excess_volatility = float(excess.std(ddof=1) * np.sqrt(periods_per_year)) if len(values) > 1 else 0.0
    sharpe = float(excess.mean() * periods_per_year / excess_volatility) if excess_volatility > 0 else 0.0
    downside_deviation = float(np.sqrt(np.square(np.minimum(excess, 0.0)).mean()) * np.sqrt(periods_per_year))
    sortino = float(excess.mean() * periods_per_year / downside_deviation) if downside_deviation > 0 else 0.0

    # Include starting capital in the high-water mark, so an initial loss is a drawdown.
    equity = pd.concat([pd.Series([1.0]), (1.0 + values).cumprod().reset_index(drop=True)], ignore_index=True)
    drawdown = equity / equity.cummax() - 1.0
    max_drawdown = float(drawdown.min())
    calmar = annualized_return / abs(max_drawdown) if max_drawdown < 0 else 0.0
    lower_tail_count = max(1, int(np.ceil(0.05 * len(values))))
    lower_tail = np.sort(values.to_numpy(dtype=float))[:lower_tail_count]
    metrics = {
        "observation_count": int(len(values)),
        "total_return": float(total_return),
        "annualized_return": float(annualized_return),
        "annualized_volatility": volatility,
        "sharpe": sharpe,
        "sortino": sortino,
        "max_drawdown": max_drawdown,
        "calmar": float(calmar),
        "value_at_risk_95": float(np.quantile(values, 0.05)),
        "expected_shortfall_95": float(np.mean(lower_tail)),
    }

    if aligned_benchmark is not None:
        benchmark_wealth = float((1.0 + aligned_benchmark).prod())
        active = values - aligned_benchmark
        tracking_error = float(active.std(ddof=1) * np.sqrt(periods_per_year)) if len(active) > 1 else 0.0
        information_ratio = float(active.mean() * periods_per_year / tracking_error) if tracking_error > 0 else 0.0
        metrics.update(
            {
                "benchmark_total_return": benchmark_wealth - 1.0,
                "benchmark_relative_compounded_return": wealth / benchmark_wealth - 1.0,
                "excess_wealth_difference": wealth - benchmark_wealth,
                "information_ratio": information_ratio,
            }
        )
    return metrics


def cost_sensitivity(
    asset_returns: pd.Series,
    signals: pd.Series,
    benchmark_returns: pd.Series | None = None,
    base_cost_bps: float = 5.0,
    multipliers: tuple[float, ...] = (1.0, 2.0, 4.0),
    periods_per_year: int = 252,
) -> DataFrame:
    """Re-run one frozen signal at several transaction-cost assumptions."""
    if base_cost_bps < 0:
        raise ValueError("base_cost_bps must be non-negative")
    if not multipliers or any(multiplier <= 0 for multiplier in multipliers):
        raise ValueError("multipliers must be a non-empty sequence of positive values")
    rows = []
    for multiplier in multipliers:
        cost_bps = base_cost_bps * multiplier
        result = backtest(asset_returns, signals, transaction_cost_bps=cost_bps)
        rows.append(
            {
                "cost_multiplier": multiplier,
                "transaction_cost_bps": cost_bps,
                "annual_turnover": float(result.turnover.mean() * periods_per_year) if len(result.turnover) else 0.0,
                "total_cost": float(result.costs.sum()),
                **performance_metrics(
                    result.returns,
                    benchmark_returns=benchmark_returns,
                    periods_per_year=periods_per_year,
                ),
            }
        )
    return pd.DataFrame(rows)
