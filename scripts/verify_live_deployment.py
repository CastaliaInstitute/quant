#!/usr/bin/env python3
"""Wait for the public Quant. Pages site and live-cell Worker to serve over HTTPS."""
from __future__ import annotations

import argparse
import json
import ssl
import sys
import time
import urllib.error
import urllib.request


def read_url(url: str, timeout: float) -> tuple[int, str, bytes]:
    request = urllib.request.Request(url, headers={"User-Agent": "QuantLab-deployment-check/1.0"})
    with urllib.request.urlopen(request, timeout=timeout, context=ssl.create_default_context()) as response:
        return response.status, response.headers.get("Content-Type", ""), response.read(1_000_000)


def verify_site(url: str) -> None:
    status, content_type, body = read_url(url, timeout=15)
    if status != 200 or "text/html" not in content_type:
        raise RuntimeError(f"research book returned HTTP {status} with {content_type!r}")
    if b"Quant." not in body:
        raise RuntimeError("research book response does not contain the expected Quant. brand")


def verify_worker(url: str) -> None:
    status, content_type, body = read_url(url, timeout=15)
    if status != 200 or "application/json" not in content_type:
        raise RuntimeError(f"cell Worker returned HTTP {status} with {content_type!r}")
    try:
        payload = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError("cell Worker health response is not valid JSON") from error
    if payload.get("status") != "ok" or payload.get("runtime") != "bounded-python-cells":
        raise RuntimeError("cell Worker health response does not match the expected runtime")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-url", default="https://quant.castalia.institute/")
    parser.add_argument("--worker-health-url", default="https://cells.quant.castalia.institute/health")
    parser.add_argument("--timeout", type=int, default=360, help="maximum wait for DNS and TLS provisioning")
    parser.add_argument("--interval", type=int, default=10, help="seconds between verification attempts")
    args = parser.parse_args()
    if args.timeout < 0 or args.interval < 1:
        raise SystemExit("timeout must be non-negative and interval must be positive")

    deadline = time.monotonic() + args.timeout
    attempt = 0
    while True:
        attempt += 1
        failures: list[str] = []
        for label, check in (("research book", lambda: verify_site(args.site_url)),
                             ("cell Worker", lambda: verify_worker(args.worker_health_url))):
            try:
                check()
                print(f"Verified {label} over HTTPS")
            except (OSError, urllib.error.URLError, RuntimeError) as error:
                failures.append(f"{label}: {error}")
        if not failures:
            print("Quant. production routes are serving successfully.")
            return
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            print("Deployment verification failed after waiting for DNS/TLS propagation:", file=sys.stderr)
            for failure in failures:
                print(f"- {failure}", file=sys.stderr)
            raise SystemExit(1)
        print(f"Attempt {attempt} did not pass; retrying in {min(args.interval, remaining):.0f}s: {'; '.join(failures)}")
        time.sleep(min(args.interval, remaining))


if __name__ == "__main__":
    main()
