"""Small, explicit long-or-cash daily backtest primitives."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class BacktestResult:
    returns: pd.Series
    positions: pd.Series
    equity: pd.Series


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
        return BacktestResult(empty, empty, empty)

    positions = aligned["signal"].clip(0.0, 1.0).shift(1).fillna(0.0)
    turnover = positions.diff().abs()
    turnover.iloc[0] = positions.iloc[0]
    costs = turnover * (transaction_cost_bps / 10_000.0)
    strategy_returns = positions * aligned["asset_return"] - costs
    equity = (1.0 + strategy_returns).cumprod()
    return BacktestResult(strategy_returns.rename("strategy_return"), positions.rename("position"), equity.rename("equity"))


def performance_metrics(returns: pd.Series, periods_per_year: int = 252) -> dict[str, float]:
    """Calculate annualized return, volatility, Sharpe, and maximum drawdown."""
    values = returns.dropna().astype(float)
    if values.empty:
        return {"annualized_return": 0.0, "annualized_volatility": 0.0, "sharpe": 0.0, "max_drawdown": 0.0}
    equity = (1.0 + values).cumprod()
    annualized_return = float(equity.iloc[-1] ** (periods_per_year / len(values)) - 1.0)
    volatility = float(values.std(ddof=1) * np.sqrt(periods_per_year)) if len(values) > 1 else 0.0
    mean = float(values.mean() * periods_per_year)
    sharpe = mean / volatility if volatility > 0 else 0.0
    drawdown = equity / equity.cummax() - 1.0
    return {
        "annualized_return": annualized_return,
        "annualized_volatility": volatility,
        "sharpe": float(sharpe),
        "max_drawdown": float(drawdown.min()),
    }
