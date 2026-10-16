#!/usr/bin/env python3
"""Fetch local historical daily bars through Alpaca or MarketData.app.

Credentials are read from APCA_API_KEY_ID / APCA_API_SECRET_KEY (Alpaca) or
MARKETDATA_TOKEN (MarketData.app). Bars are written under data/raw, which is
git-ignored; review provider terms before sharing derived output.
"""
from __future__ import annotations

import argparse
import csv
import getpass
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
MARKETDATA_KEYCHAIN_SERVICE = "QuantLab MarketData.app"
MARKETDATA_KEYCHAIN_ACCOUNT = "MARKETDATA_TOKEN"


def marketdata_keychain_token() -> str | None:
    """Read the optional macOS login-Keychain token without printing it."""
    if sys.platform != "darwin":
        return None
    result = subprocess.run(
        [
            "/usr/bin/security",
            "find-generic-password",
            "-s",
            MARKETDATA_KEYCHAIN_SERVICE,
            "-a",
            MARKETDATA_KEYCHAIN_ACCOUNT,
            "-w",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()
    return None


def mapped_symbols() -> list[str]:
    """Resolve the current issuer universe and related tickers from tracked CSVs."""
    symbols = {"SPY", "XBI"}
    for filename, ticker_field in (("universe.csv", "ticker"), ("public_events.csv", "ticker")):
        path = ROOT / "data/biopharma" / filename
        with path.open(newline="", encoding="utf-8-sig") as stream:
            for row in csv.DictReader(stream):
                symbol = (row.get(ticker_field) or "").strip().upper()
                if symbol:
                    symbols.add(symbol)
                related = (row.get("related_tickers") or "").strip().upper()
                symbols.update(part.strip() for part in re.split(r"[;,]", related) if part.strip())
    return sorted(symbols)


def event_data_range() -> tuple[str, str]:
    """Cover a year before the earliest readout and two weeks after the last."""
    path = ROOT / "data/biopharma/public_events.csv"
    with path.open(newline="", encoding="utf-8-sig") as stream:
        dates = [
            datetime.strptime(row["event_date"], "%Y-%m-%d").date()
            for row in csv.DictReader(stream)
            if row.get("event_date")
        ]
    if not dates:
        raise SystemExit("No dated rows in data/biopharma/public_events.csv; provide --start and --end explicitly.")
    return (
        (min(dates) - timedelta(days=365)).isoformat(),
        (max(dates) + timedelta(days=14)).isoformat(),
    )


def fetch_marketdata(symbols: list[str], start: str, end: str, token: str) -> tuple[list[dict], int]:
    """Fetch fully split/dividend-adjusted daily candles from MarketData.app."""
    rows: list[dict] = []
    requests = 0
    for symbol in symbols:
        query = urllib.parse.urlencode({
            "from": start,
            "to": end,
            "adjustsplits": "true",
            "adjustdividends": "true",
        })
        url = f"https://api.marketdata.app/v1/stocks/candles/D/{urllib.parse.quote(symbol)}/?{query}"
        request = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        })
        with urllib.request.urlopen(request, timeout=60) as response:
            # MarketData.app may return 203 for a cached success; urllib treats
            # both 200 and 203 as successful HTTP responses.
            payload = json.load(response)
        requests += 1
        if payload.get("s") == "error":
            raise SystemExit(f"MarketData.app rejected {symbol}: {payload.get('errmsg', 'unknown API error')}")
        if payload.get("s") not in {"ok", "no_data"}:
            raise SystemExit(f"Unexpected MarketData.app response for {symbol}: status={payload.get('s')!r}")
        times = payload.get("t", [])
        closes = payload.get("c", [])
        volumes = payload.get("v", [])
        if not (len(times) == len(closes) == len(volumes)):
            raise SystemExit(f"MarketData.app returned misaligned candle arrays for {symbol}")
        for timestamp, close, volume in zip(times, closes, volumes):
            session_date = datetime.fromtimestamp(int(timestamp), ZoneInfo("America/New_York")).date().isoformat()
            rows.append({"date": session_date, "symbol": symbol, "adjusted_close": close, "volume": volume})
    return rows, requests


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbols", default=None, help="comma-separated tickers; defaults to trial/event mappings plus SPY and XBI")
    parser.add_argument("--start", default=None, help="default: earliest event date minus 365 calendar days")
    parser.add_argument("--end", default=None, help="default: latest event date plus 14 calendar days")
    parser.add_argument("--provider", choices=("alpaca", "marketdata"), default="alpaca")
    parser.add_argument("--feed", choices=("iex", "sip"), default="sip")
    parser.add_argument("--output", type=Path, default=ROOT / "data/raw/market_prices.csv")
    parser.add_argument("--manifest", type=Path, default=ROOT / "data/raw/market-data-manifest.json")
    args = parser.parse_args()
    key = os.environ.get("APCA_API_KEY_ID")
    secret = os.environ.get("APCA_API_SECRET_KEY")
    marketdata_token = os.environ.get("MARKETDATA_TOKEN")
    if args.provider == "marketdata" and not marketdata_token:
        marketdata_token = marketdata_keychain_token()
    if args.provider == "alpaca" and (not key or not secret):
        raise SystemExit("Set APCA_API_KEY_ID and APCA_API_SECRET_KEY, or pass --provider marketdata with MARKETDATA_TOKEN.")
    if args.provider == "marketdata" and not marketdata_token:
        if not sys.stdin.isatty():
            raise SystemExit("Run interactively to enter the hidden MarketData.app token prompt, or set MARKETDATA_TOKEN in your local shell.")
        marketdata_token = getpass.getpass("MarketData.app API token (input hidden): ").strip()
        if not marketdata_token:
            raise SystemExit("No MarketData.app token entered.")
    symbols = (
        sorted({symbol.strip().upper() for symbol in args.symbols.split(",") if symbol.strip()})
        if args.symbols else mapped_symbols()
    )
    if not symbols:
        raise SystemExit("provide at least one ticker symbol")
    default_start, default_end = event_data_range() if args.start is None or args.end is None else (None, None)
    start = args.start or default_start
    end = args.end or default_end
    pages = 0
    if args.provider == "marketdata":
        rows, pages = fetch_marketdata(symbols, start, end, marketdata_token or "")
        provider = "MarketData.app"
        endpoint = "GET https://api.marketdata.app/v1/stocks/candles/D/{symbol}/"
        adjustment = "CRSP-style fully adjusted (splits and dividends)"
        feed = "provider historical daily candles"
        data_note = "Provider OHLCV terms apply. File is local and not for public redistribution; confirm license for intended research and derived outputs."
    else:
        query: dict[str, str] = {
            "symbols": ",".join(symbols), "timeframe": "1Day", "start": start,
            "end": end, "adjustment": "all", "feed": args.feed,
            "limit": "10000", "sort": "asc",
        }
        rows = []
        while True:
            url = "https://data.alpaca.markets/v2/stocks/bars?" + urllib.parse.urlencode(query)
            request = urllib.request.Request(url, headers={
                "APCA-API-KEY-ID": key or "",
                "APCA-API-SECRET-KEY": secret or "",
                "Accept": "application/json",
            })
            with urllib.request.urlopen(request, timeout=60) as response:
                page = json.load(response)
            pages += 1
            for symbol, bars in page.get("bars", {}).items():
                for bar in bars:
                    rows.append({"date": bar["t"][:10], "symbol": symbol, "adjusted_close": bar["c"], "volume": bar["v"]})
            token = page.get("next_page_token")
            if not token:
                break
            query["page_token"] = token
        provider = "Alpaca Market Data API"
        endpoint = "GET https://data.alpaca.markets/v2/stocks/bars"
        adjustment = "all"
        feed = args.feed
        data_note = "OHLCV market data is subject to provider and exchange terms; this local file is not for public redistribution."
    if not rows:
        raise SystemExit("The provider returned no bars; check ticker entitlement, feed, and date range.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=("date", "symbol", "adjusted_close", "volume"))
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda item: (item["symbol"], item["date"])))
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps({
        "provider": provider,
        "endpoint": endpoint,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "symbols": symbols,
        "start": start,
        "end": end,
        "timeframe": "1Day",
        "feed": feed,
        "adjustment": adjustment,
        "pages": pages,
        "bar_count": len(rows),
        "csv_sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(),
        "license_review_status": "unverified",
        "data_note": data_note,
    }, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {len(rows)} local daily bars for {len(symbols)} symbols to {args.output}")
    print(f"Provider={provider}; feed={feed}; adjustment={adjustment}; requests/pages={pages}.")
    print("Review the provider license before marking this dataset approved_for_research or sharing derived results.")


if __name__ == "__main__":
    main()
