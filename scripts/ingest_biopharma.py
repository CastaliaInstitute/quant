#!/usr/bin/env python3
"""Fetch a pinned biotech/pharma trial cohort and linked publication metadata.

ClinicalTrials.gov and Europe PMC records are saved locally under data/raw/.
Market prices are intentionally sourced separately from a provider licensed for
the user's intended use. See book/data-sources.md before publishing derived work.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UNIVERSE = ROOT / "data" / "biopharma" / "universe.csv"
OUT = ROOT / "data" / "raw"
CTG = "https://clinicaltrials.gov/api/v2"
EUROPE_PMC = "https://www.ebi.ac.uk/europepmc/webservices/rest"
SEC_SUBMISSIONS = "https://data.sec.gov/submissions"


def sec_company_filings(cik: str, ticker: str, company: str) -> list[dict[str, str]]:
    """Fetch timestamped 8-K/6-K accession metadata for one issuer."""
    normalized_cik = str(cik).strip().zfill(10)
    if not normalized_cik.isdigit():
        raise ValueError(f"invalid SEC CIK for {ticker}: {cik}")
    request = urllib.request.Request(
        f"{SEC_SUBMISSIONS}/CIK{normalized_cik}.json",
        headers={"User-Agent": "QuantLabAI research contact research@castalia.institute"},
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        submissions = json.load(response)
    filings = submissions.get("filings", {})
    sources = [filings.get("recent", {})]
    for historical in filings.get("files", []):
        filename = historical.get("name", "")
        if not filename or not filename.endswith(".json"):
            continue
        request = urllib.request.Request(
            f"{SEC_SUBMISSIONS}/{filename}",
            headers={"User-Agent": "QuantLabAI research contact research@castalia.institute"},
        )
        with urllib.request.urlopen(request, timeout=45) as response:
            sources.append(json.load(response))
        time.sleep(0.15)
    rows: list[dict[str, str]] = []
    for source in sources:
        count = len(source.get("accessionNumber", []))
        for index in range(count):
            form = str(source.get("form", [""] * count)[index])
            if form not in {"8-K", "6-K"}:
                continue
            accession = str(source.get("accessionNumber", [""] * count)[index])
            accepted = str(source.get("acceptanceDateTime", [""] * count)[index])
            precision = "timestamp" if accepted else "date_only_conservative_end_of_day_utc"
            if not accepted:
                filing_date = str(source.get("filingDate", [""] * count)[index])
                accepted = f"{filing_date}T23:59:59Z" if filing_date else ""
            accession_path = accession.replace("-", "")
            cik_path = str(int(normalized_cik))
            primary_document = str(source.get("primaryDocument", [""] * count)[index])
            rows.append({
                "ticker": ticker,
                "issuer": company,
                "cik": normalized_cik,
                "form": form,
                "filing_date": str(source.get("filingDate", [""] * count)[index]),
                "report_date": str(source.get("reportDate", [""] * count)[index]),
                "accepted_at_utc": accepted,
                "availability_precision": precision,
                "accession_number": accession,
                "primary_document": primary_document,
                "source_url": f"https://www.sec.gov/Archives/edgar/data/{cik_path}/{accession_path}/{primary_document}",
                "availability_note": "SEC acceptance timestamp is treated as public-availability time; verify event-specific press release timing independently.",
            })
    return rows


def fetch_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": "QuantLabAI/0.1 research; contact repository maintainer"})
    with urllib.request.urlopen(request, timeout=45) as response:
        return json.load(response)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--universe", type=Path, default=UNIVERSE)
    parser.add_argument("--output", type=Path, default=OUT)
    parser.add_argument("--pause", type=float, default=0.25)
    parser.add_argument("--with-sec-filings", action="store_true", help="also fetch issuer 8-K/6-K filing metadata; universe needs a cik column")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    with args.universe.open(newline="", encoding="utf-8") as stream:
        universe = list(csv.DictReader(stream))
    if not universe:
        raise SystemExit("universe file has no study rows")

    version = fetch_json(f"{CTG}/version")
    trials: list[dict] = []
    pmids: set[str] = set()
    fields = ",".join((
        "NCTId", "BriefTitle", "OfficialTitle", "Phase", "OverallStatus",
        "StudyFirstPostDate", "ResultsFirstPostDate", "LastUpdatePostDate",
        "PrimaryCompletionDate", "EnrollmentCount", "Condition", "InterventionName",
        "PrimaryOutcomeMeasure", "ReferencePMID",
    ))
    for row in universe:
        nct = row["nct_id"].strip().upper()
        if not nct.startswith("NCT"):
            raise SystemExit(f"invalid NCT id: {nct}")
        record = fetch_json(f"{CTG}/studies/{urllib.parse.quote(nct)}?{urllib.parse.urlencode({'fields': fields})}")
        (args.output / f"{nct}.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        protocol = record.get("protocolSection", {})
        ident = protocol.get("identificationModule", {})
        status = protocol.get("statusModule", {})
        sponsor = protocol.get("sponsorCollaboratorsModule", {})
        design = protocol.get("designModule", {})
        outcomes = protocol.get("outcomesModule", {})
        conditions = protocol.get("conditionsModule", {})
        interventions = protocol.get("armsInterventionsModule", {}).get("interventions", [])
        refs = protocol.get("referencesModule", {}).get("references", [])
        for ref in refs:
            if ref.get("pmid"):
                pmids.add(str(ref["pmid"]))
        trials.append({
            **row,
            "title": ident.get("briefTitle"),
            "official_title": ident.get("officialTitle"),
            "lead_sponsor": sponsor.get("leadSponsor", {}).get("name"),
            "study_type": design.get("studyType"),
            "phases": "|".join(design.get("phases", [])),
            "overall_status": status.get("overallStatus"),
            "study_first_post_date": status.get("studyFirstPostDateStruct", {}).get("date"),
            "primary_completion_date": status.get("primaryCompletionDateStruct", {}).get("date"),
            "results_first_post_date": status.get("resultsFirstPostDateStruct", {}).get("date"),
            "enrollment": design.get("enrollmentInfo", {}).get("count"),
            "conditions": "|".join(conditions.get("conditions", [])),
            "interventions": "|".join(i.get("name", "") for i in interventions),
            "primary_outcomes": "|".join(
                o.get("measure", "") for o in outcomes.get("primaryOutcomes", [])
            ),
            "linked_pmids": "|".join(str(ref["pmid"]) for ref in refs if ref.get("pmid")),
            "ctg_last_update_post_date": status.get("lastUpdatePostDateStruct", {}).get("date"),
        })
        time.sleep(args.pause)

    sec_filings: list[dict[str, str]] = []
    if args.with_sec_filings:
        if not all(str(row.get("cik", "")).strip() for row in universe):
            raise SystemExit("--with-sec-filings requires a cik column in the universe CSV")
        for row in universe:
            sec_filings.extend(sec_company_filings(row["cik"], row["ticker"], row["issuer"]))
            time.sleep(args.pause)

    with (args.output / "trials.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(trials[0]))
        writer.writeheader()
        writer.writerows(trials)
    publications: list[dict] = []
    sorted_pmids = sorted(pmids)
    for offset in range(0, len(sorted_pmids), 50):
        batch = sorted_pmids[offset:offset + 50]
        query = " OR ".join(f"EXT_ID:{pmid}" for pmid in batch)
        result = fetch_json(f"{EUROPE_PMC}/search?{urllib.parse.urlencode({'query': query, 'format': 'json', 'pageSize': 1000})}")
        for paper in result.get("resultList", {}).get("result", []):
            if str(paper.get("pmid", "")) not in pmids:
                continue
            publications.append({
                "pmid": str(paper.get("pmid", "")),
                "title": paper.get("title"),
                "author_string": paper.get("authorString"),
                "journal": paper.get("journalTitle"),
                "first_publication_date": paper.get("firstPublicationDate"),
                "doi": paper.get("doi"),
                "is_open_access": paper.get("isOpenAccess"),
                "source": "Europe PMC REST API",
            })
        time.sleep(args.pause)
    with (args.output / "publications.csv").open("w", newline="", encoding="utf-8") as stream:
        columns = list(publications[0]) if publications else [
            "pmid", "title", "author_string", "journal", "first_publication_date", "doi", "is_open_access", "source"
        ]
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(publications)
    if args.with_sec_filings:
        with (args.output / "sec_filings.csv").open("w", newline="", encoding="utf-8") as stream:
            columns = list(sec_filings[0]) if sec_filings else [
                "ticker", "issuer", "cik", "form", "filing_date", "report_date", "accepted_at_utc",
                "availability_precision", "accession_number", "primary_document", "source_url", "availability_note",
            ]
            writer = csv.DictWriter(stream, fieldnames=columns)
            writer.writeheader()
            writer.writerows(sec_filings)
    manifest = {
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "clinicaltrials_gov_api_version": version.get("apiVersion"),
        "clinicaltrials_gov_data_timestamp": version.get("dataTimestamp"),
        "study_ids": [row["nct_id"].upper() for row in universe],
        "universe_sha256": hashlib.sha256(args.universe.read_bytes()).hexdigest(),
        "public_event_catalog_sha256": hashlib.sha256((ROOT / "data" / "biopharma" / "public_events.csv").read_bytes()).hexdigest(),
        "study_count": len(trials),
        "linked_pubmed_ids": sorted(pmids),
        "publication_record_count": len(publications),
        "sec_filings_enabled": args.with_sec_filings,
        "sec_filing_metadata_count": len(sec_filings),
        "sec_filings_sha256": hashlib.sha256((args.output / "sec_filings.csv").read_bytes()).hexdigest() if args.with_sec_filings else None,
        "market_prices": "not fetched; import a licensed provider export before building the event panel",
        "data_limitation": "The current-record API is not a point-in-time version archive; use archived snapshots or verified disclosure timestamps for historical features.",
    }
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {len(trials)} trial records and {len(publications)} linked publication records under {args.output}")
    print(f"ClinicalTrials.gov data timestamp: {version.get('dataTimestamp')}")
    print("No market prices fetched; see the data-source guide for licensed price input.")


if __name__ == "__main__":
    main()
