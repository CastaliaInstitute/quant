#!/usr/bin/env python3
"""Join curated public catalyst timestamps, trial metadata, and licensed price bars.

Input price CSV columns: date, symbol, adjusted_close (optional volume). A raw
close-only export requires the explicit --allow-unadjusted-close option.
The event return spans the last close before the public event date to the second
close on/after it; pre-event features stop strictly before the event date.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from datetime import datetime, time, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MARKET_MODEL_ESTIMATION_SESSIONS = 200
MARKET_MODEL_GAP_SESSIONS = 30
MARKET_MODEL_MINIMUM_OBSERVATIONS = 120


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise SystemExit(f"Required input not found: {path}")
    return pd.read_csv(path)


def market_model_event_metrics(
    prices: pd.DataFrame,
    issuer_bars: pd.DataFrame,
    event_index: int,
    price_column: str,
    benchmark_symbols: dict[str, str],
) -> dict[str, object]:
    """Fit a pre-event two-factor market model and score event-window residuals.

    The estimation window is fixed at sessions [-230, -31] relative to event
    session 0, with at least 120 complete observations and a 30-session gap.
    This output is a
    descriptive event-study outcome, never an input to the pre-event model.
    """
    missing: dict[str, object] = {
        "market_model_estimation_observations": 0,
        "market_model_estimation_start": "",
        "market_model_estimation_end": "",
        "market_model_alpha_daily": np.nan,
        "market_model_beta_market": np.nan,
        "market_model_beta_sector": np.nan,
        "abnormal_return_event_session": np.nan,
        "abnormal_return_next_session": np.nan,
        "cumulative_abnormal_return_0_1": np.nan,
        "cumulative_abnormal_return_m1_1": np.nan,
        "market_model_status": "unavailable",
    }
    if not {"market", "sector"}.issubset(benchmark_symbols):
        missing["market_model_status"] = "requires_market_and_sector_benchmarks"
        return missing
    if event_index + 1 >= len(issuer_bars):
        missing["market_model_status"] = "event_window_out_of_range"
        return missing

    issuer_dates = pd.DatetimeIndex(issuer_bars.date)
    issuer_returns = issuer_bars[price_column].astype(float).pct_change().to_numpy()
    factor_returns: list[np.ndarray] = []
    for factor_name in ("market", "sector"):
        factor = prices.loc[prices.symbol == benchmark_symbols[factor_name], ["date", price_column]]
        factor_series = factor.set_index("date")[price_column].astype(float).sort_index().pct_change()
        factor_returns.append(factor_series.reindex(issuer_dates).to_numpy(dtype=float))

    estimation_end = event_index - MARKET_MODEL_GAP_SESSIONS
    estimation_start = max(1, estimation_end - MARKET_MODEL_ESTIMATION_SESSIONS)
    if estimation_end <= estimation_start:
        missing["market_model_status"] = "insufficient_pre_event_history"
        return missing
    positions = np.arange(estimation_start, estimation_end)
    response = issuer_returns[positions]
    factors = np.column_stack([values[positions] for values in factor_returns])
    complete = np.isfinite(response) & np.isfinite(factors).all(axis=1)
    response = response[complete]
    factors = factors[complete]
    if len(response) < MARKET_MODEL_MINIMUM_OBSERVATIONS:
        missing["market_model_estimation_observations"] = int(len(response))
        missing["market_model_status"] = "insufficient_complete_estimation_observations"
        return missing

    design = np.column_stack([np.ones(len(response)), factors])
    coefficients, _, rank, _ = np.linalg.lstsq(design, response, rcond=None)
    if rank < design.shape[1]:
        missing["market_model_estimation_observations"] = int(len(response))
        missing["market_model_status"] = "rank_deficient_factor_design"
        return missing

    event_positions = np.array([event_index, event_index + 1])
    event_response = issuer_returns[event_positions]
    event_factors = np.column_stack([values[event_positions] for values in factor_returns])
    if not np.isfinite(event_response).all() or not np.isfinite(event_factors).all():
        missing["market_model_estimation_observations"] = int(len(response))
        missing["market_model_status"] = "missing_event_or_benchmark_return"
        return missing
    abnormal = event_response - np.column_stack([np.ones(2), event_factors]) @ coefficients

    pre_positions = np.array([event_index - 1])
    pre_response = issuer_returns[pre_positions]
    pre_factors = np.column_stack([values[pre_positions] for values in factor_returns])
    pre_abnormal = (
        pre_response - np.column_stack([np.ones(len(pre_positions)), pre_factors]) @ coefficients
        if np.isfinite(pre_response).all() and np.isfinite(pre_factors).all()
        else np.array([], dtype=float)
    )
    return {
        "market_model_estimation_observations": int(len(response)),
        "market_model_estimation_start": pd.Timestamp(issuer_dates[positions[complete][0]]).date().isoformat(),
        "market_model_estimation_end": pd.Timestamp(issuer_dates[positions[complete][-1]]).date().isoformat(),
        "market_model_alpha_daily": float(coefficients[0]),
        "market_model_beta_market": float(coefficients[1]),
        "market_model_beta_sector": float(coefficients[2]),
        "abnormal_return_event_session": float(abnormal[0]),
        "abnormal_return_next_session": float(abnormal[1]),
        "cumulative_abnormal_return_0_1": float(abnormal.sum()),
        "cumulative_abnormal_return_m1_1": float(pre_abnormal.sum() + abnormal.sum()) if len(pre_abnormal) == 1 else np.nan,
        "market_model_status": "ok",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events", type=Path, default=ROOT / "data/biopharma/public_events.csv")
    parser.add_argument("--trials", type=Path, default=ROOT / "data/raw/trials.csv")
    parser.add_argument("--publications", type=Path, default=ROOT / "data/raw/publications.csv")
    parser.add_argument("--trial-versions", type=Path, default=ROOT / "data/biopharma/trial_versions.schema.csv")
    parser.add_argument("--research-evidence", type=Path, default=ROOT / "data/biopharma/research_evidence.schema.csv")
    parser.add_argument("--sec-filings", type=Path, default=ROOT / "data/raw/sec_filings.csv")
    parser.add_argument("--prices", type=Path, default=ROOT / "data/raw/market_prices.csv")
    parser.add_argument("--price-manifest", type=Path, default=ROOT / "data/raw/market-data-manifest.json")
    parser.add_argument(
        "--allow-unadjusted-close",
        action="store_true",
        help="allow a close-only input and mark the result as using unadjusted prices",
    )
    parser.add_argument("--market-benchmark", default="SPY", help="Broad-market ticker in the price input; blank disables")
    parser.add_argument("--sector-benchmark", default="XBI", help="Biotech-sector ticker in the price input; blank disables")
    parser.add_argument("--output", type=Path, default=ROOT / "data/processed/event_panel.csv")
    args = parser.parse_args()
    events = read_csv(args.events).fillna("")
    trials = read_csv(args.trials)
    publications = read_csv(args.publications)
    trial_versions = read_csv(args.trial_versions) if args.trial_versions.exists() else pd.DataFrame()
    research_evidence = read_csv(args.research_evidence) if args.research_evidence.exists() else pd.DataFrame()
    sec_filings = read_csv(args.sec_filings) if args.sec_filings.exists() else pd.DataFrame()
    prices = read_csv(args.prices)
    if not args.price_manifest.exists():
        raise SystemExit(
            f"Price manifest not found: {args.price_manifest}; provide the provider's manifest "
            "or a local manifest with provider, adjustment, license_review_status, and csv_sha256."
        )
    price_manifest = json.loads(args.price_manifest.read_text(encoding="utf-8"))
    if not price_manifest.get("provider"):
        raise SystemExit("Price manifest must identify the data provider")
    if not price_manifest.get("adjustment"):
        raise SystemExit("Price manifest must document its corporate-action adjustment policy")
    if price_manifest.get("csv_sha256") != hashlib.sha256(args.prices.read_bytes()).hexdigest():
        raise SystemExit("Price manifest csv_sha256 does not match the supplied price CSV")
    if price_manifest.get("license_review_status") != "approved_for_research":
        raise SystemExit(
            "Price manifest license_review_status must be approved_for_research after reviewing "
            "the provider's terms for this intended research use"
        )
    required = {"date", "symbol"}
    if not required.issubset(prices.columns):
        raise SystemExit(f"Price input needs columns: {', '.join(sorted(required))}")
    if "adjusted_close" in prices.columns:
        price_column = "adjusted_close"
        price_basis = "adjusted_close"
    elif "close" in prices.columns and args.allow_unadjusted_close:
        price_column = "close"
        price_basis = "unadjusted_close_explicitly_allowed"
    elif "close" in prices.columns:
        raise SystemExit(
            "Price input contains only close. Supply adjusted_close, or pass "
            "--allow-unadjusted-close to explicitly accept unadjusted prices."
        )
    else:
        raise SystemExit("Price input needs an adjusted_close column")
    prices["date"] = pd.to_datetime(prices["date"], errors="coerce").dt.normalize()
    prices["symbol"] = prices["symbol"].astype(str).str.upper()
    prices[price_column] = pd.to_numeric(prices[price_column], errors="coerce")
    prices = prices.dropna(subset=["date", price_column]).sort_values(["symbol", "date"])
    if (prices[price_column] <= 0).any():
        raise SystemExit("Price bars must be positive")
    if prices.duplicated(["symbol", "date"]).any():
        raise SystemExit("Price input must contain at most one selected bar per symbol/date")
    benchmark_symbols = {
        name: str(value).strip().upper()
        for name, value in (("market", args.market_benchmark), ("sector", args.sector_benchmark))
        if str(value).strip()
    }
    missing_benchmarks = sorted(set(benchmark_symbols.values()) - set(prices.symbol))
    if missing_benchmarks:
        raise SystemExit(
            "Price input is missing benchmark symbol(s): " + ", ".join(missing_benchmarks)
            + ". Fetch them with --symbols or pass an empty benchmark option to disable."
        )
    required_issuers = set(events.ticker.astype(str).str.strip().str.upper())
    related_issuers: set[str] = set()
    if "related_tickers" in events.columns:
        for value in events.related_tickers.astype(str):
            related_issuers.update(
                part.strip().upper() for part in value.replace(";", ",").split(",") if part.strip()
            )
    missing_issuers = sorted((required_issuers | related_issuers) - set(prices.symbol))
    if missing_issuers:
        raise SystemExit("Price input is missing event or related issuer symbol(s): " + ", ".join(missing_issuers))
    if "nct_id" not in trials or trials.nct_id.astype(str).str.upper().duplicated().any():
        raise SystemExit("Current-trial input must have one row per nct_id")
    if "pmid" not in publications:
        raise SystemExit("Publication metadata input needs a pmid column")
    trial_by_id = trials.assign(nct_id=trials.nct_id.astype(str).str.upper()).set_index("nct_id").to_dict("index")
    paper_dates = {
        str(row.pmid): pd.to_datetime(row.first_publication_date, errors="coerce")
        for row in publications.itertuples()
    }
    if not trial_versions.empty:
        required_versions = {
            "nct_id", "version_id", "public_available_at_utc", "source_url", "record_sha256",
            "phase", "enrollment", "conditions", "interventions", "primary_outcomes",
        }
        if not required_versions.issubset(trial_versions.columns):
            raise SystemExit(f"Trial-version input missing columns: {', '.join(sorted(required_versions - set(trial_versions.columns)))}")
        trial_versions["nct_id"] = trial_versions.nct_id.astype(str).str.upper()
        trial_versions["public_available_at_utc"] = pd.to_datetime(
            trial_versions.public_available_at_utc, utc=True, errors="coerce"
        )
        if trial_versions.public_available_at_utc.isna().any():
            raise SystemExit("Trial-version public_available_at_utc must contain valid UTC timestamps")
        if trial_versions.duplicated(["nct_id", "version_id"]).any():
            raise SystemExit("Trial-version input contains duplicate (nct_id, version_id) rows")
        if not trial_versions.record_sha256.astype(str).str.fullmatch(r"[0-9a-fA-F]{64}").all():
            raise SystemExit("Each trial-version record_sha256 must be a 64-character SHA-256 hex digest")
    if not research_evidence.empty:
        required_evidence = {
            "nct_id", "pmid", "doi", "version_id", "public_available_at_utc", "source_url",
            "record_sha256", "evidence_role", "evidence_class", "pre_event_features_json",
        }
        if not required_evidence.issubset(research_evidence.columns):
            raise SystemExit(f"Research-evidence input missing columns: {', '.join(sorted(required_evidence - set(research_evidence.columns)))}")
        research_evidence["nct_id"] = research_evidence.nct_id.astype(str).str.upper()
        research_evidence["public_available_at_utc"] = pd.to_datetime(
            research_evidence.public_available_at_utc, utc=True, errors="coerce"
        )
        if research_evidence.public_available_at_utc.isna().any():
            raise SystemExit("Research-evidence public_available_at_utc must contain valid UTC timestamps")
        if not research_evidence.record_sha256.astype(str).str.fullmatch(r"[0-9a-fA-F]{64}").all():
            raise SystemExit("Each research-evidence record_sha256 must be a 64-character SHA-256 hex digest")
        research_evidence["evidence_class"] = research_evidence.evidence_class.astype(str).str.lower()
        if not research_evidence.evidence_class.isin({"preclinical", "clinical", "review"}).all():
            raise SystemExit("Research evidence_class must be preclinical, clinical, or review")
        try:
            parsed = research_evidence.pre_event_features_json.map(json.loads)
        except (TypeError, ValueError) as exc:
            raise SystemExit("Research pre_event_features_json must contain valid JSON") from exc
        if not parsed.map(lambda value: isinstance(value, dict)).all():
            raise SystemExit("Research pre_event_features_json must contain JSON objects")
    if not sec_filings.empty:
        required_sec = {"ticker", "form", "accepted_at_utc", "accession_number", "source_url"}
        if not required_sec.issubset(sec_filings.columns):
            raise SystemExit(f"SEC filing input missing columns: {', '.join(sorted(required_sec - set(sec_filings.columns)))}")
        sec_filings["ticker"] = sec_filings.ticker.astype(str).str.upper()
        sec_filings["form"] = sec_filings.form.astype(str).str.upper()
        sec_filings["accepted_at_utc"] = pd.to_datetime(sec_filings.accepted_at_utc, utc=True, errors="coerce")
        if sec_filings.accepted_at_utc.isna().any():
            raise SystemExit("SEC accepted_at_utc must contain valid UTC timestamps")
        if not sec_filings.form.isin({"8-K", "6-K"}).all():
            raise SystemExit("SEC filing input may contain only 8-K and 6-K rows")
        if sec_filings.duplicated(["ticker", "accession_number"]).any():
            raise SystemExit("SEC filing input contains duplicate ticker/accession rows")
    rows: list[dict] = []
    for event in events.to_dict("records"):
        ticker = str(event["ticker"]).upper()
        bars = prices.loc[prices.symbol == ticker].sort_values("date").reset_index(drop=True)
        if len(bars) < 22:
            continue
        dates = bars.date.to_numpy(dtype="datetime64[ns]")
        anchor = np.datetime64(pd.Timestamp(event["event_date"]).normalize())
        event_cutoff = None
        if event.get("event_time_local") and event.get("event_timezone"):
            local_time = datetime.strptime(f"{event['event_date']} {event['event_time_local']}", "%Y-%m-%d %H:%M")
            event_cutoff = local_time.replace(tzinfo=ZoneInfo(event["event_timezone"])).astimezone(timezone.utc)
            event_local_ny = event_cutoff.astimezone(ZoneInfo("America/New_York"))
            if event_local_ny.time() >= time(16, 0):
                next_date = pd.Timestamp(event_local_ny.date()) + pd.Timedelta(days=1)
                anchor = np.datetime64(next_date.normalize())
        event_index = int(np.searchsorted(dates, anchor, side="left"))
        prior_index = event_index - 1
        if prior_index < 20 or event_index + 1 >= len(bars):
            continue
        close = bars[price_column].to_numpy(dtype=float)
        ret = pd.Series(close).pct_change().to_numpy()
        features = {
            "pre_event_return_5d": float(close[prior_index] / close[prior_index - 5] - 1.0),
            "pre_event_return_20d": float(close[prior_index] / close[prior_index - 20] - 1.0),
            "pre_event_volatility_20d": float(np.std(ret[prior_index - 19:prior_index + 1], ddof=1) * np.sqrt(252)),
            "event_session_return": float(close[event_index] / close[prior_index] - 1.0),
            "next_session_return": float(close[event_index + 1] / close[event_index] - 1.0),
            "two_session_event_window_return": float(close[event_index + 1] / close[prior_index] - 1.0),
            "absolute_two_session_move": float(abs(close[event_index + 1] / close[prior_index] - 1.0)),
            "down_10pct_event_window": int(close[event_index + 1] / close[prior_index] - 1.0 <= -0.10),
            "matched_first_session": pd.Timestamp(dates[event_index]).date().isoformat(),
            "matched_second_session": pd.Timestamp(dates[event_index + 1]).date().isoformat(),
            "features_asof": pd.Timestamp(dates[prior_index]).date().isoformat(),
        }
        if "volume" in bars:
            volume = pd.to_numeric(bars.volume, errors="coerce").to_numpy(dtype=float)
            base = np.nanmean(volume[max(0, prior_index - 19):prior_index])
            features["pre_event_relative_volume"] = float(volume[prior_index] / base) if base > 0 else np.nan
        matched_dates = pd.DatetimeIndex(bars.date.iloc[[prior_index, event_index, event_index + 1]])
        for benchmark_name, benchmark_symbol in benchmark_symbols.items():
            benchmark = prices.loc[prices.symbol == benchmark_symbol].set_index("date")[price_column].sort_index()
            aligned = benchmark.reindex(matched_dates)
            if aligned.isna().any():
                raise SystemExit(
                    f"{benchmark_name} benchmark {benchmark_symbol} lacks a bar on an issuer matched session; "
                    "provide a complete calendar-aligned file or disable that benchmark explicitly."
                )
            benchmark_close = aligned.to_numpy(dtype=float)
            features[f"{benchmark_name}_pre_event_return_20d"] = np.nan
            history_dates = pd.DatetimeIndex(bars.date.iloc[prior_index - 20:prior_index + 1])
            history = benchmark.reindex(history_dates)
            if history.notna().all() and len(history) == 21:
                features[f"{benchmark_name}_pre_event_return_20d"] = float(history.iloc[-1] / history.iloc[0] - 1.0)
            features[f"{benchmark_name}_event_window_return"] = float(benchmark_close[2] / benchmark_close[0] - 1.0)
            features[f"{benchmark_name}_event_session_return"] = float(benchmark_close[1] / benchmark_close[0] - 1.0)
            features[f"{benchmark_name}_next_session_return"] = float(benchmark_close[2] / benchmark_close[1] - 1.0)
            features[f"issuer_minus_{benchmark_name}_event_window_return"] = float(
                features["two_session_event_window_return"] - features[f"{benchmark_name}_event_window_return"]
            )
        trial = trial_by_id.get(event["nct_id"], {})
        trial_pmids = [pmid for pmid in str(trial.get("linked_pmids", "")).split("|") if pmid]
        event_date = pd.Timestamp(event["event_date"]).normalize()
        linked_dates = [paper_dates[pmid].normalize() for pmid in trial_pmids if pmid in paper_dates and not pd.isna(paper_dates[pmid])]
        feature_cutoff_local = datetime.combine(
            pd.Timestamp(dates[prior_index]).date(), time(16, 0),
            tzinfo=ZoneInfo("America/New_York"),
        )
        feature_cutoff_utc = pd.Timestamp(feature_cutoff_local).tz_convert("UTC")
        versions = trial_versions.loc[
            (trial_versions.nct_id == event["nct_id"])
            & (trial_versions.public_available_at_utc < feature_cutoff_utc)
        ] if not trial_versions.empty else trial_versions
        point_in_time_trial = versions.sort_values("public_available_at_utc").tail(1).iloc[0].to_dict() if len(versions) else {}
        phase_text = str(point_in_time_trial.get("phase", "")).upper()
        phase_numbers = [int(value) for value in re.findall(r"PHASE\s*([1-4])", phase_text)]
        trial_phase_stage = float(max(phase_numbers)) if phase_numbers else np.nan
        trial_enrollment = pd.to_numeric(point_in_time_trial.get("enrollment", np.nan), errors="coerce")
        trial_design_features = {
            "trial_enrollment_asof_event": float(trial_enrollment) if pd.notna(trial_enrollment) else np.nan,
            "trial_primary_outcome_count_asof_event": float(len([v for v in str(point_in_time_trial.get("primary_outcomes", "")).split("|") if v.strip()])) if point_in_time_trial else np.nan,
            "trial_condition_count_asof_event": float(len([v for v in str(point_in_time_trial.get("conditions", "")).split("|") if v.strip()])) if point_in_time_trial else np.nan,
            "trial_intervention_count_asof_event": float(len([v for v in str(point_in_time_trial.get("interventions", "")).split("|") if v.strip()])) if point_in_time_trial else np.nan,
        }
        evidence = research_evidence.loc[
            (research_evidence.nct_id == event["nct_id"])
            & (research_evidence.public_available_at_utc < feature_cutoff_utc)
        ] if not research_evidence.empty else research_evidence
        evidence = evidence.sort_values("public_available_at_utc") if len(evidence) else evidence
        if len(evidence):
            paper_date_by_pmid = {key: value.normalize() for key, value in paper_dates.items() if not pd.isna(value)}
            evidence = evidence.loc[evidence.apply(
                lambda row: str(row.pmid) not in paper_date_by_pmid
                or paper_date_by_pmid[str(row.pmid)].date() <= row.public_available_at_utc.date(), axis=1
            )]
            # Only explicitly curated pre-event evidence can become a model input.
            evidence = evidence.loc[evidence.evidence_role.astype(str).str.lower().isin({"pre_event", "primary", "secondary"})]
        evidence_roles = evidence.evidence_role.astype(str).str.lower() if len(evidence) else pd.Series(dtype=str)
        evidence_role_counts = {
            f"research_role_{role}_count_asof_event": int(evidence_roles.eq(role).sum())
            for role in ("pre_event", "primary", "secondary")
        }
        evidence_classes = evidence.evidence_class.astype(str).str.lower() if len(evidence) else pd.Series(dtype=str)
        evidence_class_counts = {
            f"research_class_{evidence_class}_count_asof_event": int(evidence_classes.eq(evidence_class).sum())
            for evidence_class in ("preclinical", "clinical", "review")
        }
        research_numeric_values: dict[str, list[float]] = {}
        for item in evidence.get("pre_event_features_json", []):
            record = json.loads(item)
            for key, value in record.items():
                if not str(key).replace("_", "").isalnum():
                    raise SystemExit(f"Invalid research feature name: {key}")
                # Only numeric, explicitly curated, point-in-time measurements can
                # enter the model matrix. Text remains in the traceable record JSON.
                if isinstance(value, (int, float)) and not isinstance(value, bool) and np.isfinite(value):
                    research_numeric_values.setdefault(str(key), []).append(float(value))
        research_features = {
            f"research_numeric_{key}_median": float(np.median(values))
            for key, values in research_numeric_values.items() if values
        }
        research_hashes = [str(value) for value in evidence.get("record_sha256", [])]
        market_model_metrics = market_model_event_metrics(prices, bars, event_index, price_column, benchmark_symbols)
        abnormal_car = market_model_metrics["cumulative_abnormal_return_0_1"]
        issuer_filings = sec_filings.loc[
            (sec_filings.ticker == ticker)
            & (sec_filings.accepted_at_utc < feature_cutoff_utc)
        ].copy() if not sec_filings.empty else sec_filings
        if len(issuer_filings):
            days_before_cutoff = (feature_cutoff_utc - issuer_filings.accepted_at_utc).dt.total_seconds() / 86400.0
            recent_30d = days_before_cutoff.le(30)
            recent_90d = days_before_cutoff.le(90)
            latest_idx = issuer_filings.accepted_at_utc.idxmax()
            latest_filing = issuer_filings.loc[latest_idx]
            filing_context = {
                "issuer_filing_count_30d": int(recent_30d.sum()),
                "issuer_filing_count_90d": int(recent_90d.sum()),
                "issuer_8k_count_90d": int((recent_90d & issuer_filings.form.eq("8-K")).sum()),
                "issuer_6k_count_90d": int((recent_90d & issuer_filings.form.eq("6-K")).sum()),
                "issuer_days_since_last_filing": float((feature_cutoff_utc - latest_filing.accepted_at_utc).total_seconds() / 86400.0),
                "issuer_last_filing_accession_asof_event": str(latest_filing.accession_number),
                "issuer_last_filing_source_asof_event": str(latest_filing.source_url),
            }
        elif not sec_filings.empty:
            filing_context = {
                "issuer_filing_count_30d": 0,
                "issuer_filing_count_90d": 0,
                "issuer_8k_count_90d": 0,
                "issuer_6k_count_90d": 0,
                "issuer_days_since_last_filing": np.nan,
                "issuer_last_filing_accession_asof_event": "",
                "issuer_last_filing_source_asof_event": "",
            }
        else:
            filing_context = {
                "issuer_filing_count_30d": np.nan,
                "issuer_filing_count_90d": np.nan,
                "issuer_8k_count_90d": np.nan,
                "issuer_6k_count_90d": np.nan,
                "issuer_days_since_last_filing": np.nan,
                "issuer_last_filing_accession_asof_event": "",
                "issuer_last_filing_source_asof_event": "",
            }
        rows.append({
            **event,
            "current_registry_title_hindsight_annotation": trial.get("title"),
            "current_registry_phase_hindsight_annotation": trial.get("phases"),
            "current_registry_conditions_hindsight_annotation": trial.get("conditions"),
            "current_registry_interventions_hindsight_annotation": trial.get("interventions"),
            "current_registry_enrollment_hindsight_annotation": trial.get("enrollment"),
            "current_registry_primary_outcome_count_hindsight_annotation": len(str(trial.get("primary_outcomes", "")).split("|")) if trial.get("primary_outcomes") else 0,
            "current_registry_results_post_date_hindsight_annotation": trial.get("results_first_post_date"),
            "current_registry_linked_paper_count_hindsight_annotation": len(linked_dates),
            "current_registry_linked_papers_dated_before_event_hindsight_annotation": sum(date <= event_date for date in linked_dates),
            "current_registry_linked_papers_dated_after_event_hindsight_annotation": sum(date > event_date for date in linked_dates),
            "point_in_time_trial_version_available": bool(point_in_time_trial),
            "feature_cutoff_utc": feature_cutoff_utc.isoformat(),
            "disclosure_timestamp_utc": pd.Timestamp(event_cutoff).isoformat() if event_cutoff else "",
            "trial_version_id_asof_event": point_in_time_trial.get("version_id"),
            "trial_version_sha256_asof_event": point_in_time_trial.get("record_sha256"),
            "trial_phase_asof_event": point_in_time_trial.get("phase"),
            "trial_phase_stage_asof_event": trial_phase_stage,
            "trial_enrollment_asof_event": trial_design_features["trial_enrollment_asof_event"],
            "trial_conditions_asof_event": point_in_time_trial.get("conditions"),
            "trial_interventions_asof_event": point_in_time_trial.get("interventions"),
            "trial_primary_outcomes_asof_event": point_in_time_trial.get("primary_outcomes"),
            "point_in_time_research_record_count": int(len(evidence)),
            **evidence_role_counts,
            **evidence_class_counts,
            "research_pmids_asof_event": "|".join(str(value) for value in evidence.get("pmid", [])),
            "research_feature_records_asof_event": json.dumps(
                [json.loads(value) for value in evidence.get("pre_event_features_json", [])],
                sort_keys=True,
            ),
            "research_record_hashes_asof_event": "|".join(research_hashes),
            **filing_context,
            **trial_design_features,
            "price_field_used": price_column,
            "market_data_rows_available": len(bars),
            **market_model_metrics,
            "down_10pct_market_model_car_0_1": int(abnormal_car <= -0.10) if np.isfinite(abnormal_car) else np.nan,
            **research_features,
            **features,
        })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(args.output, index=False)
    inputs = {
        "events": args.events,
        "trials": args.trials,
        "publications": args.publications,
        "prices": args.prices,
        "price_manifest": args.price_manifest,
    }
    for key, path in (("trial_versions", args.trial_versions), ("research_evidence", args.research_evidence), ("sec_filings", args.sec_filings)):
        if path.exists():
            inputs[key] = path
    manifest = {
        "evidence_status": "historical_event_panel_requires_manual_timestamp_and_coverage_review",
        "row_count": len(rows),
        "panel_sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(),
        "price_field": price_column,
        "price_basis": price_basis,
        "benchmark_symbols": benchmark_symbols,
        "event_study_model": {
            "method": "OLS issuer simple returns on SPY and XBI simple returns",
            "estimation_window": f"event sessions -230 through -31, at most {MARKET_MODEL_ESTIMATION_SESSIONS} sessions; 30-session gap",
            "minimum_complete_observations": MARKET_MODEL_MINIMUM_OBSERVATIONS,
            "event_windows": {"car_0_1": "event session through next session", "car_m1_1": "one session before through next session"},
            "role": "descriptive outcomes only; never eligible pre-event model features",
        },
        "input_sha256": {key: hashlib.sha256(path.read_bytes()).hexdigest() for key, path in inputs.items()},
        "input_paths": {key: str(path.resolve()) for key, path in inputs.items()},
        "price_manifest": {
            "provider": price_manifest["provider"],
            "adjustment": price_manifest["adjustment"],
            "license_review_status": price_manifest["license_review_status"],
            "csv_sha256": price_manifest["csv_sha256"],
            "manifest_sha256": hashlib.sha256(args.price_manifest.read_bytes()).hexdigest(),
        },
        "cutoff_convention": "prior matched regular-session close; 16:00 America/New_York",
        "latest_registry_fields": "hindsight annotations only; excluded from model features",
        "market_data_redistribution": "Check provider license; raw/processed market data stays local by default.",
    }
    manifest_path = args.output.with_suffix(".manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(rows)} event rows to {args.output}")
    print("These event windows are descriptive and too small for generalizable ML; review source timestamps and market-data licensing.")


if __name__ == "__main__":
    main()
