#!/usr/bin/env python3
"""Audit the public CTO human-label cohort without treating it as a base rate.

The source CSV is downloaded into ignored data/raw/cto/. The committed output
contains aggregate lineage and coverage only, never row-level clinical data.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from urllib.request import Request, urlopen

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
REVISION = "6b080abb5a510e8a6573085f4b843e08ac3b6204"
SOURCE_PATH = "human_labels_2020_2024/human_labels_2020_2024.csv"
SOURCE_URL = f"https://huggingface.co/datasets/chufangao/CTO/resolve/{REVISION}/{SOURCE_PATH}"
EXPECTED_SHA256 = "c51b9c455de8c0befc07bc3ec58ba4b09da35767fd7f0d9f2ecb048cdb51fc47"


def download_range_csv(destination: Path, chunk_size: int = 800_000) -> None:
    """Download a pinned file with byte ranges and validate every response."""
    probe = Request(SOURCE_URL, headers={"Range": "bytes=0-0"})
    with urlopen(probe, timeout=90) as response:
        content_range = response.headers.get("Content-Range", "")
        match = re.fullmatch(r"bytes 0-0/(\d+)", content_range)
        if response.status != 206 or not match or response.read() != b"n":
            raise RuntimeError(f"Unexpected range-probe response: {response.status}, {content_range}")
        total_size = int(match.group(1))

    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as output:
        for start in range(0, total_size, chunk_size):
            end = min(total_size - 1, start + chunk_size - 1)
            request = Request(SOURCE_URL, headers={"Range": f"bytes={start}-{end}"})
            with urlopen(request, timeout=90) as response:
                data = response.read()
                content_range = response.headers.get("Content-Range", "")
            expected_range = f"bytes {start}-{end}/{total_size}"
            if response.status != 206 or content_range != expected_range or len(data) != end - start + 1:
                raise RuntimeError(f"Unexpected range response: wanted {expected_range}, got {content_range}")
            output.write(data)


def label_crosstab(data: pd.DataFrame, group_column: str) -> dict[str, dict[str, int | float]]:
    """Describe selected-cohort labels by a field without treating it as a predictor."""
    table = pd.crosstab(data[group_column].fillna("<missing>").astype(str), data["labels"])
    output: dict[str, dict[str, int | float]] = {}
    for group, row in table.iterrows():
        negatives = int(row.get(0, row.get(0.0, 0)))
        positives = int(row.get(1, row.get(1.0, 0)))
        n = negatives + positives
        output[str(group)] = {
            "label_0_count": negatives,
            "label_1_count": positives,
            "count": n,
            "label_1_fraction_in_selected_cohort": positives / n if n else 0.0,
        }
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "data/raw/cto/human_labels_2020_2024.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "reports/cto-human-labels-audit.json")
    args = parser.parse_args()
    if not args.input.exists():
        download_range_csv(args.input)

    digest = hashlib.sha256(args.input.read_bytes()).hexdigest()
    if digest != EXPECTED_SHA256:
        raise SystemExit(f"Pinned CTO CSV SHA-256 mismatch: {digest}")
    data = pd.read_csv(args.input, low_memory=False)
    required = {"nct_id", "phase", "labels", "overall_status", "completion_year", "study_first_posted_date"}
    if not required.issubset(data.columns):
        raise SystemExit(f"CTO source missing columns: {', '.join(sorted(required - set(data.columns)))}")
    if data.nct_id.astype(str).duplicated().any():
        raise SystemExit("CTO human-label cohort has duplicate nct_id rows")
    if data.labels.isna().any() or not data.labels.isin([0, 1]).all():
        raise SystemExit("CTO human-label cohort must contain complete binary 0/1 labels")

    # This deliberately computes a forbidden, post-outcome probe to quantify
    # target leakage in the available snapshot. It is never a model baseline.
    status_prediction = data.overall_status.eq("COMPLETED").astype(int)
    status_accuracy = float((status_prediction == data.labels.astype(int)).mean())
    sponsor_counts = data.source.fillna("<missing>").value_counts()

    output = {
        "dataset": "Clinical Trial Outcome (CTO), human_labels_2020_2024",
        "dataset_revision": REVISION,
        "source_url": SOURCE_URL,
        "source_sha256": digest,
        "row_count": int(len(data)),
        "unique_trials": int(data.nct_id.nunique()),
        "label_counts_in_selected_cohort": {str(key): int(value) for key, value in data.labels.value_counts(dropna=False).sort_index().items()},
        "phase_counts_in_selected_cohort": {str(key): int(value) for key, value in data.phase.value_counts(dropna=False).sort_index().items()},
        "status_counts_in_selected_cohort": {str(key): int(value) for key, value in data.overall_status.value_counts(dropna=False).sort_index().items()},
        "completion_year_counts": {str(key): int(value) for key, value in data.completion_year.value_counts(dropna=False).sort_index().items()},
        "label_by_phase_in_selected_cohort": label_crosstab(data, "phase"),
        "label_by_current_status_in_selected_cohort": label_crosstab(data, "overall_status"),
        "label_by_completion_year_in_selected_cohort": label_crosstab(data, "completion_year"),
        "sponsor_coverage": {
            "unique_sponsors": int(data.source.nunique(dropna=True)),
            "top_10_sponsor_rows": int(sponsor_counts.head(10).sum()),
            "top_10_sponsor_share": float(sponsor_counts.head(10).sum() / len(data)),
        },
        "forbidden_current_status_leakage_probe": {
            "rule": "predict success (1) when current overall_status is COMPLETED; otherwise predict failure (0)",
            "accuracy_in_selected_cohort": status_accuracy,
            "status_label_table": label_crosstab(data, "overall_status"),
            "allowed_as_predictive_baseline": False,
            "interpretation": "Leakage diagnostic only: current status is a post-outcome field and the cohort's label process uses status-based rules. The apparent accuracy is not forecast skill.",
        },
        "study_first_posted_date_min": str(data.study_first_posted_date.min()),
        "study_first_posted_date_max": str(data.study_first_posted_date.max()),
        "modeling_disposition": "external clinical-outcome benchmark only; no return modeling and no RL transition probabilities fitted",
        "selection_caveat": "The authors describe a manually annotated subset that applies prior rule-based filtering to remove easy cases. Its label prevalence is not a population success-rate prior.",
        "temporal_caveat": "The extract contains current registry metadata and outcome-derived fields; it is not a point-in-time feature archive. Use only after a separate leakage audit and do not use status, completion, results-posting, or post-outcome fields as predictors.",
        "market_data_caveat": "The cohort does not supply verified first-public-disclosure timestamps or daily security return histories; it cannot calibrate market reaction or trading reward.",
        "excluded_fields_for_pre_outcome_prediction": [
            "overall_status", "last_known_status", "completion_date", "completion_year",
            "primary_completion_date", "results_first_submitted_date", "results_first_posted_date",
            "disposition_first_submitted_date", "disposition_first_posted_date", "why_stopped",
            "last_update_posted_date", "created_at", "updated_at", "labels",
        ],
        "point_in_time_feature_disposition": {
            "verified_as_of_first_public_posting": [],
            "candidate_fields_requiring_archived_record_version_review": [
                "phase", "enrollment", "enrollment_type", "number_of_arms", "source", "source_class",
                "has_dmc", "is_fda_regulated_drug", "baseline_population", "brief_title", "official_title",
            ],
            "interpretation": "This pinned CSV is a current metadata extract, not an archived first-posted study version. No trial covariate is admitted to a pre-outcome model until its historical version and availability date are verified.",
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(output, indent=2) + "\n"
    args.output.write_text(rendered, encoding="utf-8")
    published = ROOT / "book/_static/cto-human-labels-audit.json"
    published.write_text(rendered, encoding="utf-8")
    print(f"Audited {len(data)} selected trial labels; wrote aggregate report to {args.output}")
    print("This selected cohort is not used as a clinical success prior or market-return training set.")


if __name__ == "__main__":
    main()
