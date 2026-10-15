#!/usr/bin/env python3
"""Summarize curated AI-exposure and outcome coverage without claiming causality."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "data/biopharma/ai_evidence.csv"
OUTCOMES = ROOT / "data/biopharma/ai_outcomes.csv"
OUTPUT = ROOT / "book/_static/ai-impact-monitor.json"
EVIDENCE_REQUIRED = {
    "record_id", "entity_type", "entity_id", "ai_application_class",
    "ai_involvement_level", "evidence_type", "public_available_at_utc",
    "public_time_precision", "source_url", "record_sha256", "review_status", "taxonomy_version",
}
OUTCOME_REQUIRED = {
    "outcome_id", "entity_type", "entity_id", "outcome_domain", "metric",
    "observed_value", "unit", "comparison_group", "comparison_value",
    "comparison_unit", "observation_start", "observation_end",
    "ai_exposure_contrast",
    "public_available_at_utc", "public_time_precision", "source_url", "source_sha256", "study_design",
    "review_status",
}


def read_ledger(path: Path, required: set[str]) -> tuple[list[dict[str, str]], str]:
    if not path.exists():
        return [], "missing"
    raw = path.read_bytes()
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or [])
        missing = sorted(required - fields)
        if missing:
            raise SystemExit(f"{path}: missing required columns: {', '.join(missing)}")
        rows = list(reader)
    return rows, hashlib.sha256(raw).hexdigest()


def present(row: dict[str, str], *fields: str) -> bool:
    return all((row.get(field) or "").strip() for field in fields)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, default=EVIDENCE)
    parser.add_argument("--outcomes", type=Path, default=OUTCOMES)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()

    evidence, evidence_hash = read_ledger(args.evidence, EVIDENCE_REQUIRED)
    outcomes, outcomes_hash = read_ledger(args.outcomes, OUTCOME_REQUIRED)
    reviewed_evidence = [r for r in evidence if r.get("review_status", "").lower() == "reviewed"]
    dated_evidence = [
        r for r in reviewed_evidence
        if present(r, "public_available_at_utc", "public_time_precision", "source_url", "record_sha256")
    ]
    timestamped_evidence = [r for r in dated_evidence if r.get("public_time_precision", "").lower() == "date_and_time"]
    comparison_ready = [
        r for r in outcomes
        if r.get("review_status", "").lower() == "reviewed"
        and present(r, "comparison_group", "comparison_value", "comparison_unit", "study_design")
    ]
    domain_rows: dict[str, list[dict[str, str]]] = {}
    for row in outcomes:
        domain_rows.setdefault((row.get("outcome_domain") or "unspecified").strip(), []).append(row)
    impact_domains = {
        "scientific": {"clinical_trial_measure", "clinical_progression", "drug_discovery"},
        "operational": {"trial_operations", "development_timeline", "development_cost"},
        "economic": {"company_value", "market_response", "revenue"},
    }
    impact_coverage = {}
    for impact, known_domains in impact_domains.items():
        matching = [row for domain in known_domains for row in domain_rows.get(domain, [])]
        reviewed = [row for row in matching if row.get("review_status", "").lower() == "reviewed"]
        comparable = [row for row in reviewed if present(row, "comparison_group", "comparison_value", "comparison_unit", "study_design")]
        direct_ai_contrasts = [row for row in comparable if row.get("ai_exposure_contrast", "").strip().lower() == "yes"]
        impact_coverage[impact] = {
            "outcome_records": len(matching),
            "reviewed_records": len(reviewed),
            "reviewed_comparator_records": len(comparable),
            "direct_ai_exposure_contrasts": len(direct_ai_contrasts),
            "estimate_available": False,
        }
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "coverage_only",
        "interpretation": (
            "This audit measures curated evidence coverage. It does not estimate the causal effect of AI; "
            "observational comparisons remain vulnerable to selection, confounding, and publication bias."
        ),
        "exposure_ledger": {
            "path": str(args.evidence.relative_to(ROOT)) if args.evidence.is_relative_to(ROOT) else str(args.evidence),
            "sha256": evidence_hash,
            "records": len(evidence),
            "reviewed_records": len(reviewed_evidence),
            "dated_records": len(dated_evidence),
            "exact_timestamp_records": len(timestamped_evidence),
            "application_classes": dict(sorted(Counter((r.get("ai_application_class") or "unspecified") for r in evidence).items())),
            "review_status": dict(sorted(Counter((r.get("review_status") or "unspecified") for r in evidence).items())),
        },
        "outcome_ledger": {
            "path": str(args.outcomes.relative_to(ROOT)) if args.outcomes.is_relative_to(ROOT) else str(args.outcomes),
            "sha256": outcomes_hash,
            "records": len(outcomes),
            "domains": dict(sorted(Counter((r.get("outcome_domain") or "unspecified") for r in outcomes).items())),
            "reviewed_with_comparator_and_design": len(comparison_ready),
            "impact_lanes": impact_coverage,
        },
        "causal_effect_estimate_available": False,
        "current_case_note": "Rentosertib is one AI-attributed candidate with a randomized molecule-versus-placebo outcome; that trial comparison does not isolate AI's contribution.",
        "direct_ai_exposure_comparison_available": any(row.get("ai_exposure_contrast", "").strip().lower() == "yes" for row in comparison_ready),
        "gates": {
            "molecule_or_trial_level_exposure": len(dated_evidence) > 0,
            "reviewed_comparator_outcomes": len(comparison_ready) > 0,
            "direct_ai_exposure_comparison": any(row.get("ai_exposure_contrast", "").strip().lower() == "yes" for row in comparison_ready),
            "matched_cohort_and_sensitivity_analysis": False,
            "sufficient_historical_market_data": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote AI impact coverage audit: {args.output}")
    print(f"Exposure rows: {len(evidence)} ({len(dated_evidence)} reviewed and dated; {len(timestamped_evidence)} with exact timestamps); outcome rows: {len(outcomes)}")
    print("No causal impact estimate is computed by this audit.")


if __name__ == "__main__":
    main()
