#!/usr/bin/env python3
"""Fetch local historical daily bars through the official Alpaca data API.

Requires an Alpaca market-data entitlement and APCA_API_KEY_ID /
APCA_API_SECRET_KEY in the local environment. Bars are written under data/raw,
which is git-ignored; check the provider agreement before sharing derived output.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbols", default=None, help="comma-separated tickers; defaults to trial/event mappings plus SPY and XBI")
    parser.add_argument("--start", default=None, help="default: earliest event date minus 365 calendar days")
    parser.add_argument("--end", default=None, help="default: latest event date plus 14 calendar days")
    parser.add_argument("--feed", choices=("iex", "sip"), default="sip")
    parser.add_argument("--output", type=Path, default=ROOT / "data/raw/market_prices.csv")
    parser.add_argument("--manifest", type=Path, default=ROOT / "data/raw/market-data-manifest.json")
    args = parser.parse_args()
    key = os.environ.get("APCA_API_KEY_ID")
    secret = os.environ.get("APCA_API_SECRET_KEY")
    if not key or not secret:
        raise SystemExit("Set APCA_API_KEY_ID and APCA_API_SECRET_KEY in your local shell; do not commit them.")
    symbols = (
        sorted({symbol.strip().upper() for symbol in args.symbols.split(",") if symbol.strip()})
        if args.symbols else mapped_symbols()
    )
    if not symbols:
        raise SystemExit("provide at least one ticker symbol")
    default_start, default_end = event_data_range() if args.start is None or args.end is None else (None, None)
    start = args.start or default_start
    end = args.end or default_end
    query: dict[str, str] = {
        "symbols": ",".join(symbols),
        "timeframe": "1Day",
        "start": start,
        "end": end,
        "adjustment": "all",
        "license_review_status": "unverified",
        "feed": args.feed,
        "limit": "10000",
        "sort": "asc",
    }
    rows: list[dict] = []
    pages = 0
    while True:
        url = "https://data.alpaca.markets/v2/stocks/bars?" + urllib.parse.urlencode(query)
        request = urllib.request.Request(url, headers={
            "APCA-API-KEY-ID": key,
            "APCA-API-SECRET-KEY": secret,
            "Accept": "application/json",
        })
        with urllib.request.urlopen(request, timeout=60) as response:
            page = json.load(response)
        pages += 1
        for symbol, bars in page.get("bars", {}).items():
            for bar in bars:
                rows.append({
                    "date": bar["t"][:10],
                    "symbol": symbol,
                    "adjusted_close": bar["c"],
                    "volume": bar["v"],
                })
        token = page.get("next_page_token")
        if not token:
            break
        query["page_token"] = token
    if not rows:
        raise SystemExit("The provider returned no bars; check ticker entitlement, feed, and date range.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=("date", "symbol", "adjusted_close", "volume"))
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda item: (item["symbol"], item["date"])))
    args.manifest.write_text(json.dumps({
        "provider": "Alpaca Market Data API",
        "endpoint": "GET https://data.alpaca.markets/v2/stocks/bars",
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "symbols": symbols,
        "start": start,
        "end": end,
        "timeframe": "1Day",
        "feed": args.feed,
        "adjustment": "all",
        "pages": pages,
        "bar_count": len(rows),
        "csv_sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(),
        "data_note": "OHLCV market data is subject to provider and exchange terms; this local file is not for public redistribution.",
    }, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {len(rows)} local daily bars for {len(symbols)} symbols to {args.output}")
    print(f"Feed={args.feed}; adjustment=all; pages={pages}. Review licensing before sharing derived results.")


if __name__ == "__main__":
    main()
