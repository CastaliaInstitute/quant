"""Long-only allocation baselines with explicit issuer and sector caps."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd


AllocationMethod = Literal["equal_weight", "inverse_volatility"]


@dataclass(frozen=True)
class AllocationResult:
    """Target weights; unallocated capital remains in cash."""

    weights: pd.Series
    cash_weight: float
    excluded_assets: tuple[str, ...]
    method: AllocationMethod


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
