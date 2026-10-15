"""Long-only allocation baselines with explicit issuer and sector caps."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

from .backtest import performance_metrics


AllocationMethod = Literal["equal_weight", "inverse_volatility"]


@dataclass(frozen=True)
class AllocationResult:
    """Target weights; unallocated capital remains in cash."""

    weights: pd.Series
    cash_weight: float
    excluded_assets: tuple[str, ...]
    method: AllocationMethod


@dataclass(frozen=True)
class PortfolioBacktestResult:
    """Daily portfolio returns and accounting under lagged target weights."""

    returns: pd.Series
    positions: pd.DataFrame
    cash_weights: pd.Series
    equity: pd.Series
    turnover: pd.Series
    costs: pd.Series


def allocate_portfolio(
    assets: list[str] | tuple[str, ...],
    *,
    method: AllocationMethod = "equal_weight",
    annualized_volatility: pd.Series | None = None,
    max_asset_weight: float = 0.40,
    sectors: pd.Series | None = None,
    max_sector_weight: float | None = None,
) -> AllocationResult:
    """Build a long-only equal- or inverse-volatility target portfolio.

    Caps are applied by reducing weights; excess capital stays in cash rather
    than being silently reallocated. In inverse-volatility mode, only finite,
    strictly positive volatility estimates are investable. The caller is
    responsible for fitting those estimates with information available at the
    decision time (for example, within a historical training window).
    """
    names = list(assets)
    if not names or any(not isinstance(name, str) or not name.strip() for name in names):
        raise ValueError("assets must contain non-empty string identifiers")
    if len(set(names)) != len(names):
        raise ValueError("asset identifiers must be unique")
    if not 0 < max_asset_weight <= 1:
        raise ValueError("max_asset_weight must be in (0, 1]")
    if max_sector_weight is not None and not 0 < max_sector_weight <= 1:
        raise ValueError("max_sector_weight must be in (0, 1]")
    if max_sector_weight is not None and sectors is None:
        raise ValueError("sectors are required when max_sector_weight is set")
    if method not in ("equal_weight", "inverse_volatility"):
        raise ValueError("method must be 'equal_weight' or 'inverse_volatility'")

    weights = pd.Series(0.0, index=pd.Index(names, name="asset"), dtype=float)
    excluded: tuple[str, ...] = ()
    if method == "equal_weight":
        weights[:] = 1.0 / len(names)
    else:
        if annualized_volatility is None:
            raise ValueError("inverse_volatility allocation requires annualized_volatility")
        if not annualized_volatility.index.is_unique:
            raise ValueError("volatility estimates must have unique asset identifiers")
        volatility = pd.to_numeric(annualized_volatility.reindex(names), errors="coerce").astype(float)
        eligible = np.isfinite(volatility.to_numpy(dtype=float)) & volatility.gt(0).to_numpy()
        eligible_names = [name for name, keep in zip(names, eligible) if keep]
        excluded = tuple(name for name, keep in zip(names, eligible) if not keep)
        if eligible_names:
            eligible_volatility = volatility.loc[eligible_names]
            inverse = eligible_volatility.min() / eligible_volatility
            weights.loc[eligible_names] = inverse / inverse.sum()

    weights = weights.clip(upper=max_asset_weight)
    if max_sector_weight is not None:
        if not sectors.index.is_unique:
            raise ValueError("sector assignments must have unique asset identifiers")
        sector_for_asset = sectors.reindex(names)
        eligible_names = weights.index[weights.gt(0)]
        missing_sector = sector_for_asset.loc[eligible_names].isna() | sector_for_asset.loc[eligible_names].astype(str).str.strip().eq("")
        if missing_sector.any():
            missing_names = ", ".join(sector_for_asset.loc[eligible_names][missing_sector].index.astype(str))
            raise ValueError(f"sector assignments are missing for invested assets: {missing_names}")
        group_totals = weights.loc[eligible_names].groupby(sector_for_asset.loc[eligible_names]).sum()
        for sector, total in group_totals.items():
            if total > max_sector_weight:
                group_assets = eligible_names[sector_for_asset.loc[eligible_names].eq(sector)]
                weights.loc[group_assets] *= max_sector_weight / total

    cash_weight = float(max(0.0, 1.0 - weights.sum()))
    return AllocationResult(
        weights=weights.rename("target_weight"),
        cash_weight=cash_weight,
        excluded_assets=excluded,
        method=method,
    )


def portfolio_backtest(
    asset_returns: pd.DataFrame,
    target_weights: pd.DataFrame,
    *,
    transaction_cost_bps: float = 5.0,
    cash_returns: pd.Series | None = None,
) -> PortfolioBacktestResult:
    """Backtest long-only target weights observed at close and held next period.

    Return and weight panels must share the same increasing, unique index and
    asset columns. Missing returns are permitted only for zero-weight assets;
    missing invested returns fail closed rather than becoming assumed zeros.
    Cash earns zero unless an aligned cash-return series is supplied. Turnover
    is the sum of absolute asset-weight changes; transaction costs apply to that
    traded notional at every rebalance. Target rows must sum to at most one.
    """
    if not np.isfinite(transaction_cost_bps) or transaction_cost_bps < 0:
        raise ValueError("transaction_cost_bps must be finite and non-negative")
    if asset_returns.empty or target_weights.empty:
        raise ValueError("asset returns and target weights must not be empty")
    if not asset_returns.index.is_unique or not target_weights.index.is_unique:
        raise ValueError("return and weight dates must be unique")
    if not asset_returns.index.is_monotonic_increasing or not target_weights.index.is_monotonic_increasing:
        raise ValueError("return and weight dates must be increasing")
    if not asset_returns.index.equals(target_weights.index):
        raise ValueError("return and target-weight panels must use identical dates")
    if not asset_returns.columns.is_unique or not target_weights.columns.is_unique:
        raise ValueError("asset columns must be unique")
    if set(asset_returns.columns) != set(target_weights.columns):
        raise ValueError("return and target-weight panels must have identical asset columns")

    returns = asset_returns.apply(pd.to_numeric, errors="coerce").astype(float)
    weights = target_weights.reindex(columns=asset_returns.columns).apply(pd.to_numeric, errors="coerce").astype(float)
    weight_values = weights.to_numpy(dtype=float)
    if not np.isfinite(weight_values).all():
        raise ValueError("target weights must be finite")
    if (weight_values < 0).any():
        raise ValueError("target weights must be long-only")
    if (weights.sum(axis=1) > 1.0 + 1e-10).any():
        raise ValueError("target weights must sum to at most one; excess capital belongs in cash")

    positions = weights.shift(1).fillna(0.0)
    cash_weights = (1.0 - positions.sum(axis=1)).clip(lower=0.0)
    if cash_returns is None:
        cash_return = pd.Series(0.0, index=returns.index)
    else:
        if not cash_returns.index.is_unique or not cash_returns.index.equals(returns.index):
            raise ValueError("cash returns must have the same unique dates as asset returns")
        cash_return = pd.to_numeric(cash_returns, errors="coerce").astype(float)
        if not np.isfinite(cash_return.to_numpy(dtype=float)).all() or (cash_return <= -1.0).any():
            raise ValueError("cash returns must be finite and greater than -100%")

    finite_returns = pd.DataFrame(
        np.isfinite(returns.to_numpy(dtype=float)), index=returns.index, columns=returns.columns
    )
    invested_missing = positions.gt(0.0) & ~finite_returns
    if invested_missing.to_numpy().any():
        date, asset = np.argwhere(invested_missing.to_numpy())[0]
        raise ValueError(
            f"missing or non-finite return for invested asset {returns.columns[asset]!r} "
            f"on {returns.index[date]!r}"
        )
    if ((returns <= -1.0) & positions.gt(0.0)).to_numpy().any():
        raise ValueError("invested asset returns must be greater than -100%")

    safe_returns = returns.where(finite_returns, 0.0)
    gross_returns = (positions * safe_returns).sum(axis=1) + cash_weights * cash_return
    turnover = positions.diff().abs().sum(axis=1)
    turnover.iloc[0] = positions.iloc[0].abs().sum()
    costs = turnover * (transaction_cost_bps / 10_000.0)
    net_returns = gross_returns - costs
    if not np.isfinite(net_returns.to_numpy(dtype=float)).all() or (net_returns <= -1.0).any():
        raise ValueError("transaction costs and returns imply a non-finite result or a loss of 100% or more")
    equity = (1.0 + net_returns).cumprod()
    return PortfolioBacktestResult(
        returns=net_returns.rename("portfolio_return"),
        positions=positions,
        cash_weights=cash_weights.rename("cash_weight"),
        equity=equity.rename("equity"),
        turnover=turnover.rename("turnover"),
        costs=costs.rename("cost"),
    )


def portfolio_cost_sensitivity(
    asset_returns: pd.DataFrame,
    target_weights: pd.DataFrame,
    *,
    benchmark_returns: pd.Series | None = None,
    cash_returns: pd.Series | None = None,
    base_cost_bps: float = 5.0,
    multipliers: tuple[float, ...] = (1.0, 2.0, 4.0),
    periods_per_year: int = 252,
) -> pd.DataFrame:
    """Evaluate one fixed weight path under 1×/2×/4× costs and common dates."""
    if not np.isfinite(base_cost_bps) or base_cost_bps < 0:
        raise ValueError("base_cost_bps must be finite and non-negative")
    if not multipliers or any(not np.isfinite(multiplier) or multiplier <= 0 for multiplier in multipliers):
        raise ValueError("multipliers must be a non-empty sequence of positive values")
    rows = []
    for multiplier in multipliers:
        cost_bps = base_cost_bps * multiplier
        result = portfolio_backtest(
            asset_returns,
            target_weights,
            transaction_cost_bps=cost_bps,
            cash_returns=cash_returns,
        )
        rows.append({
            "cost_multiplier": multiplier,
            "transaction_cost_bps": cost_bps,
            "annual_turnover": float(result.turnover.mean() * periods_per_year),
            "total_cost": float(result.costs.sum()),
            **performance_metrics(
                result.returns,
                periods_per_year=periods_per_year,
                benchmark_returns=benchmark_returns,
            ),
        })
    return pd.DataFrame(rows)
