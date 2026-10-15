#!/usr/bin/env python3
"""Provision the Quant Pages project and move its hostname to Cloudflare Pages."""
from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.parse
import urllib.request


API = "https://api.cloudflare.com/client/v4"


def api(method: str, path: str, payload: dict | None = None) -> dict:
    token = os.environ.get("CLOUDFLARE_API_TOKEN")
    if not token:
        raise SystemExit("CLOUDFLARE_API_TOKEN is required")
    body = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(
        f"{API}{path}", data=body, method=method,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.load(response)
    except urllib.error.HTTPError as exc:
        try:
            detail = json.load(exc).get("errors", [])
        except (ValueError, AttributeError):
            detail = []
        messages = "; ".join(str(item.get("message", "")) for item in detail if item.get("message"))
        raise SystemExit(f"Cloudflare API returned HTTP {exc.code}" + (f": {messages}" if messages else "")) from None
    if not result.get("success"):
        messages = "; ".join(str(item.get("message", "")) for item in result.get("errors", []) if item.get("message"))
        raise SystemExit("Cloudflare API request failed" + (f": {messages}" if messages else ""))
    return result


def ensure_project(account_id: str, project: str, branch: str) -> None:
    path = f"/accounts/{urllib.parse.quote(account_id, safe='')}/pages/projects?per_page=100"
    projects = api("GET", path).get("result", [])
    if any(item.get("name") == project for item in projects):
        print(f"Pages project ready: {project}")
        return
    api("POST", f"/accounts/{urllib.parse.quote(account_id, safe='')}/pages/projects", {
        "name": project,
        "production_branch": branch,
    })
    print(f"Created Pages project: {project}")


def ensure_domain_and_dns(account_id: str, project: str, domain: str, zone_name: str, pages_target: str) -> None:
    account = urllib.parse.quote(account_id, safe="")
    # Validate zone visibility, current records, and conflict safety before
    # mutating Pages domain state. This prevents partial setup on missing scope.
    zone_query = urllib.parse.urlencode({"name": zone_name, "account.id": account_id, "per_page": 50})
    zones = api("GET", f"/zones?{zone_query}").get("result", [])
    exact_zones = [zone for zone in zones if zone.get("name", "").lower() == zone_name.lower()]
    if len(exact_zones) != 1:
        raise SystemExit(f"Expected one Cloudflare zone named {zone_name}; found {len(exact_zones)}")
    zone_id = exact_zones[0]["id"]
    dns_query = urllib.parse.urlencode({"name": domain, "per_page": 100})
    dns_path = f"/zones/{urllib.parse.quote(zone_id, safe='')}/dns_records?{dns_query}"
    records = api("GET", dns_path).get("result", [])
    conflicts = [record for record in records if record.get("type") != "CNAME"]
    if conflicts:
        kinds = ", ".join(sorted({str(record.get("type")) for record in conflicts}))
        raise SystemExit(f"Refusing to replace non-CNAME {domain} DNS record(s): {kinds}")
    if len(records) > 1:
        raise SystemExit(f"Refusing to modify {domain}: multiple CNAME records were returned")

    project_path = f"/accounts/{account}/pages/projects/{urllib.parse.quote(project, safe='')}/domains"
    domains = api("GET", project_path + "?per_page=100").get("result", [])
    if not any(item.get("name", "").lower() == domain.lower() for item in domains):
        api("POST", project_path, {"name": domain})
        print(f"Attached Pages custom domain: {domain}")
    else:
        print(f"Pages custom domain already attached: {domain}")

    dns_payload = {
        "type": "CNAME", "name": domain, "content": pages_target,
        "ttl": 1, "proxied": True,
    }
    if records:
        record = records[0]
        if record.get("content", "").rstrip(".").lower() == pages_target.rstrip(".").lower() and record.get("proxied") is True:
            print(f"Pages DNS record already active: {domain} → {pages_target}")
            return
        api("PATCH", f"/zones/{zone_id}/dns_records/{record['id']}", dns_payload)
        print(f"Updated Pages DNS record: {domain} → {pages_target}")
    else:
        api("POST", f"/zones/{zone_id}/dns_records", dns_payload)
        print(f"Created Pages DNS record: {domain} → {pages_target}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("prepare", "domain"), required=True)
    parser.add_argument("--project", default="quantlab")
    parser.add_argument("--branch", default="main")
    parser.add_argument("--domain", default="quant.castalia.institute")
    parser.add_argument("--zone", default="castalia.institute")
    args = parser.parse_args()
    account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    if not account_id:
        raise SystemExit("CLOUDFLARE_ACCOUNT_ID is required")
    ensure_project(account_id, args.project, args.branch)
    if args.phase == "domain":
        ensure_domain_and_dns(
            account_id, args.project, args.domain, args.zone, f"{args.project}.pages.dev"
        )


if __name__ == "__main__":
    main()
