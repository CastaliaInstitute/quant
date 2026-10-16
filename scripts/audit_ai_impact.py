#!/usr/bin/env python3
"""Summarize curated AI-exposure and outcome coverage without claiming causality."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "data/biopharma/ai_evidence.csv"
OUTCOMES = ROOT / "data/biopharma/ai_outcomes.csv"
OUTPUT = ROOT / "book/_static/ai-impact-monitor.json"
LITERATURE = ROOT / "data/biopharma/ai_literature.csv"
EVIDENCE_REQUIRED = {
    "record_id", "entity_type", "entity_id", "ai_application_class",
    "ai_involvement_level", "evidence_type", "public_available_at_utc",
    "public_time_precision", "source_url", "record_sha256", "review_status", "taxonomy_version",
}
OUTCOME_REQUIRED = {
    "outcome_id", "entity_type", "entity_id", "outcome_domain", "metric",
    "observed_value", "unit", "comparison_group", "comparison_value",
    "comparison_unit", "observation_start", "observation_end",
    "ai_exposure_contrast", "impact_dimension", "affected_group",
    "public_available_at_utc", "public_time_precision", "source_url", "source_sha256", "study_design",
    "review_status",
}
LITERATURE_REQUIRED = {
    "study_id", "title", "publication_date", "cohort_cutoff", "cohort_design",
    "asset_count", "company_count", "phase_1_completed_assets", "phase_2_completed_assets",
    "phase_3_entered_or_completed_assets", "phase_1_success_rate", "phase_2_success_rate",
    "direct_ai_comparator", "source_url", "review_status", "limitations",
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


def validate_ledger(rows: list[dict[str, str]], *, path: Path, id_field: str, hash_fields: tuple[str, ...]) -> None:
    seen: set[str] = set()
    for line, row in enumerate(rows, start=2):
        identifier = (row.get(id_field) or "").strip()
        if not identifier:
            raise SystemExit(f"{path}:{line}: {id_field} must not be empty")
        if identifier in seen:
            raise SystemExit(f"{path}:{line}: duplicate {id_field} {identifier!r}")
        seen.add(identifier)
        if id_field == "outcome_id":
            for field in ("impact_dimension", "affected_group"):
                if not (row.get(field) or "").strip():
                    raise SystemExit(f"{path}:{line}: {field} must not be empty")
        for field in hash_fields:
            value = (row.get(field) or "").strip()
            if value and not re.fullmatch(r"[0-9a-fA-F]{64}", value):
                raise SystemExit(f"{path}:{line}: {field} must be a 64-character SHA-256 hex digest")
        for field in ("public_available_at_utc",):
            value = (row.get(field) or "").strip()
            if value:
                try:
                    datetime.fromisoformat(value.replace("Z", "+00:00"))
                except ValueError as exc:
                    raise SystemExit(f"{path}:{line}: invalid ISO-8601 {field}: {value!r}") from exc


def direct_contrast(row: dict[str, str]) -> bool:
    return row.get("ai_exposure_contrast", "").strip().lower() == "yes"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, default=EVIDENCE)
    parser.add_argument("--outcomes", type=Path, default=OUTCOMES)
    parser.add_argument("--literature", type=Path, default=LITERATURE)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()

    evidence, evidence_hash = read_ledger(args.evidence, EVIDENCE_REQUIRED)
    outcomes, outcomes_hash = read_ledger(args.outcomes, OUTCOME_REQUIRED)
    literature, literature_hash = read_ledger(args.literature, LITERATURE_REQUIRED)
    validate_ledger(evidence, path=args.evidence, id_field="record_id", hash_fields=("record_sha256",))
    validate_ledger(outcomes, path=args.outcomes, id_field="outcome_id", hash_fields=("source_sha256",))
    validate_ledger(literature, path=args.literature, id_field="study_id", hash_fields=())
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
    abstract_reviewed_literature = [
        row for row in literature
        if row.get("review_status", "").lower() == "abstract_reviewed"
        and present(row, "publication_date", "cohort_cutoff", "source_url")
    ]
    latest_literature = max(
        abstract_reviewed_literature,
        key=lambda row: row["publication_date"],
        default=None,
    )
    domain_rows: dict[str, list[dict[str, str]]] = {}
    for row in outcomes:
        domain_rows.setdefault((row.get("outcome_domain") or "unspecified").strip(), []).append(row)
    impact_domains = {
        "scientific": {"clinical_trial_measure", "clinical_progression", "drug_discovery"},
        "operational": {"trial_operations", "development_timeline", "development_cost", "productivity"},
        "economic": {"company_value", "market_response", "revenue", "labor_market"},
        "patient_access_and_safety": {"patient_access", "patient_safety", "health_equity"},
        "workforce_and_society": {"labor_market", "workforce_conditions", "scientific_workforce"},
        "environmental": {"environmental_impact", "energy_use", "compute_emissions"},
    }
    economic_rows = [row for row in outcomes if row.get("outcome_domain", "").strip() == "economic"]
    pipeline_exposures = [
        row for row in dated_evidence
        if row.get("entity_type", "").strip().lower() in {"candidate", "molecule", "program", "trial"}
    ]
    pipeline_market = {
        "status": "coverage_only",
        "dated_candidate_or_trial_exposures": len(pipeline_exposures),
        "economic_outcome_records": len(economic_rows),
        "economic_outcomes_with_comparator": sum(
            present(row, "comparison_group", "comparison_value", "comparison_unit", "study_design")
            for row in economic_rows
        ),
        "direct_ai_exposure_comparisons": sum(
            direct_contrast(row) and present(row, "comparison_group", "comparison_value", "comparison_unit", "study_design")
            for row in economic_rows
        ),
        "historical_price_panel_available": (ROOT / "data/raw/market_prices.csv").exists(),
        "event_return_estimate_available": False,
        "interpretation": (
            "Tracks candidate/trial AI disclosures alongside company and market outcomes. "
            "Price reactions need timestamped, point-in-time disclosures, licensed prices, "
            "and market/biotech controls; they are not clinical impact or causal AI effects."
        ),
    }
    impact_coverage = {}
    for impact, known_domains in impact_domains.items():
        matching = [row for domain in known_domains for row in domain_rows.get(domain, [])]
        reviewed = [row for row in matching if row.get("review_status", "").lower() == "reviewed"]
        comparable = [row for row in reviewed if present(row, "comparison_group", "comparison_value", "comparison_unit", "study_design")]
        direct_ai_contrasts = [row for row in comparable if row.get("ai_exposure_contrast", "").strip().lower() == "yes"]
        impact_coverage[impact] = {
            "dimensions": dict(sorted(Counter((row.get("impact_dimension") or "unspecified").strip() for row in matching).items())),
            "affected_groups": dict(sorted(Counter((row.get("affected_group") or "unspecified").strip() for row in matching).items())),
            "outcome_records": len(matching),
            "reviewed_records": len(reviewed),
            "reviewed_comparator_records": len(comparable),
            "direct_ai_exposure_contrasts": len(direct_ai_contrasts),
            "estimate_available": False,
        }
    all_reviewed_outcomes = [row for row in outcomes if row.get("review_status", "").lower() == "reviewed"]
    reviewed_direct_contrasts = [row for row in all_reviewed_outcomes if direct_contrast(row)]
    outcome_values = Counter((row.get("ai_exposure_contrast") or "unspecified").strip().lower() for row in all_reviewed_outcomes)
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
            "ai_exposure_contrast_status": dict(sorted(outcome_values.items())),
            "reviewed_direct_ai_exposure_contrasts": len(reviewed_direct_contrasts),
            "impact_lanes": impact_coverage,
        },
        "pipeline_to_market_watch": pipeline_market,
        "literature_watch": {
            "path": str(args.literature.relative_to(ROOT)) if args.literature.is_relative_to(ROOT) else str(args.literature),
            "sha256": literature_hash,
            "studies": len(literature),
            "abstract_reviewed_studies": len(abstract_reviewed_literature),
            "studies_with_direct_ai_comparator": sum(
                row.get("direct_ai_comparator", "").strip().lower() == "yes"
                for row in abstract_reviewed_literature
            ),
            "latest_abstract_reviewed_study": latest_literature,
            "interpretation": "Published cohort summaries are context, not causal AI-effect estimates; study definitions and follow-up may differ.",
        },
        "causal_effect_estimate_available": False,
        "current_case_note": "Rentosertib is one AI-attributed candidate with a randomized molecule-versus-placebo outcome; that trial comparison does not isolate AI's contribution.",
        "direct_ai_exposure_comparison_available": any(direct_contrast(row) for row in comparison_ready),
        "gates": {
            "molecule_or_trial_level_exposure": len(dated_evidence) > 0,
            "reviewed_comparator_outcomes": len(comparison_ready) > 0,
            "direct_ai_exposure_comparison": any(direct_contrast(row) for row in comparison_ready),
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
