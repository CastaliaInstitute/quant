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
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbols", default="MRNA,PFE,AZN,NVAX,JNJ,SPY,XBI")
    parser.add_argument("--start", default="2020-10-01")
    parser.add_argument("--end", default="2021-02-10")
    parser.add_argument("--feed", choices=("iex", "sip"), default="sip")
    parser.add_argument("--output", type=Path, default=ROOT / "data/raw/market_prices.csv")
    parser.add_argument("--manifest", type=Path, default=ROOT / "data/raw/market-data-manifest.json")
    args = parser.parse_args()
    key = os.environ.get("APCA_API_KEY_ID")
    secret = os.environ.get("APCA_API_SECRET_KEY")
    if not key or not secret:
        raise SystemExit("Set APCA_API_KEY_ID and APCA_API_SECRET_KEY in your local shell; do not commit them.")
    symbols = sorted({symbol.strip().upper() for symbol in args.symbols.split(",") if symbol.strip()})
    if not symbols:
        raise SystemExit("provide at least one ticker symbol")
    query: dict[str, str] = {
        "symbols": ",".join(symbols),
        "timeframe": "1Day",
        "start": args.start,
        "end": args.end,
        "adjustment": "all",
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
                    "close": bar["c"],
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
        writer = csv.DictWriter(stream, fieldnames=("date", "symbol", "close", "volume"))
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda item: (item["symbol"], item["date"])))
    args.manifest.write_text(json.dumps({
        "provider": "Alpaca Market Data API",
        "endpoint": "GET https://data.alpaca.markets/v2/stocks/bars",
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "symbols": symbols,
        "start": args.start,
        "end": args.end,
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
