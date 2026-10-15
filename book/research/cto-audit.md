---
jupytext:
  text_representation:
    extension: .md
    format_name: myst
    format_version: '0.13'
kernelspec:
  name: python3
  display_name: Python 3
  language: python
---

# CTO Benchmark: Label Semantics and Leakage Audit

```{raw} html
<p class="castalia-kicker">SELECTED CLINICAL COHORT · TARGET AUDIT · NO FORECAST CLAIM</p>
```

The Clinical Trial Outcome (CTO) human-label file provides 11,012 recent trial records. The paper defines success around meeting primary endpoints and progressing to the next development stage, with Phase III success tied to approval. The dataset card says the 2020–2024 sample follows rule-based status and p-value filtering intended to remove easier cases before human review. It is a selected benchmark, not a population sample from which to estimate a universal success rate. [Paper](https://arxiv.org/abs/2406.10292) · [Pinned dataset card](https://huggingface.co/datasets/chufangao/CTO/tree/6b080abb5a510e8a6573085f4b843e08ac3b6204).

Quant. pins the file revision and SHA-256 in the [coverage and leakage audit](../_static/cto-human-labels-audit.json). The local source CSV is ignored by Git; the public artifact contains aggregate diagnostics only.

## A post-outcome field nearly reconstructs the label

In the selected file, 3,545 of 3,870 trials with current status `COMPLETED` have label 1; all 7,142 records currently marked `TERMINATED`, `SUSPENDED`, or `WITHDRAWN` have label 0. A deliberately forbidden rule—predict success for `COMPLETED`, failure otherwise—gets **97.05% accuracy** on this cohort.

That is a leakage demonstration, not a useful baseline. Current status is known after the clinical outcome process, and the CTO labeling methodology itself uses status-based rules. Publishing that accuracy as model skill would amount to predicting a partially status-defined label from the status used to assign it. Even among completed records, the label split is not trivial: 325 are labeled failure and 3,545 success.

The audited target count is 7,467 label-0 and 3,545 label-1 records, but those proportions describe this selected file only. Completion-year label-1 fractions range from 37.8% in 2020 to 14.6% in 2024; selection rules, follow-up maturity, and temporal changes make these unsuitable as population or simulator priors.

## Field availability policy

| Field family | Examples | Disposition for a pre-outcome model |
| --- | --- | --- |
| Label and hindsight | `labels`, `overall_status`, `last_known_status`, `why_stopped` | Exclude from predictors; status is also used as an explicit leakage probe only |
| Outcome and follow-up dates | Completion dates/year, primary completion date, results-posting dates, last-update dates | Exclude from predictors; may define outcome-time slices with a clear caveat |
| Potential trial-design covariates | Phase, enrollment, arms, DMC, FDA-regulated flags, baseline population, titles | Require the archived ClinicalTrials.gov version and its public date at the chosen feature cutoff; the pinned CSV alone does not verify that they were known then |
| Trial and sponsor identity | NCT ID, sponsor name and class | Use for joins or declared group splits, never as an unexamined proxy for label history |

The release contains current registry metadata rather than the original version for each trial. Although `study_first_posted_date` is available, that date does not prove that every other field in the same row had the same value when first posted. The current audit therefore verifies **zero** predictor fields as point-in-time safe. This is a provenance limit, not a claim that trial-design variables have no predictive value.

## Research decision

No outcome model is fitted from this CSV yet. Before a benchmark study, reconstruct candidate covariates from archived first-posted records, define outcome availability separately from trial completion, and preserve sponsor-aware and chronological evaluation. For the selected cohort, report Brier score and log loss against a prevalence baseline fitted only on each training period, calibration, phase strata, sponsor counts, and uncertainty. Do not infer issuer returns or RL transition rates from these clinical labels.

This audit is a useful result in its own right: a high score can arise from target construction and hindsight fields. The next valid step is to make information timing auditable before comparing models.
